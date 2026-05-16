# 第一個寫入類 MCP (adjust_points) 落地 + 寫入確認雙層保險設計 + tracker/cs_kb MCP 擴充 + 阿全 session 翻車救回

- 日期：2026-05-16（接續同日上午、下午兩篇的傍晚場）
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-opus-4-7)
- 相關專案：cwsoft-sqlserver-mcp、general-task-bot、cwsoft-aquan-manager、cwsoft-project-tracker（本篇所在）、cwsoft-ai-customer-service（資料端）

> 接續下午篇「第一個寫入類 MCP 建議從 adjust_points 起」的待跟進。一動就連環滾出寫入確認的設計分層、操作翻車的兩個救援、MCP 工具集擴充、per-user session 路線分歧——deliverable 比預想多。

---

## 1. adjust_points 落地：從兩段式 → 單 tool

### 初版（兩段式）

仿 sqlgate `/adjust_points` 的 GET/POST 流程，server.py 寫了 `adjust_points_preview(name, delta)` 跟 `adjust_points_commit(name, delta)`，AGENTS.md 加硬規則「preview 跟 commit 必須跨兩個 LINE turn、中間使用者明確確認」。

### colombo 質疑 → 拍板換單 tool

> 「兩段式不是沒價值、只是加扣點這種小屁事有點殺雞用牛刀了。codex 有多問一句作確認就很好。兩段式這種保障、是要給下架客戶這種毀滅性、不可逆的功能用的。」

拔掉 `_preview` + `_commit`、改一個 `adjust_points(name, delta)` 直接執行。

### 關鍵分歧釐清（中段被我誤讀過一次）

對話中段我曾把「拔機制層強制」延伸成「對話層也不必問」，被糾正。最終雙方確認的雙層分維：

| 維度 | 內容 | 寫入類 tool 適用範圍 |
|---|---|---|
| **機制層** | MCP tool 是否強制兩段式（SDK 層級、codex 無法繞過） | 不可逆 → 強制兩段；可逆 → 拔、走單 tool |
| **對話層** | codex 是否在對話中要求使用者明確確認（AGENTS.md 硬規則） | **所有寫入類都要保留**、不分可逆不可逆 |

也就是：「可逆 = 拔機制層強制」**不等於**「可逆 = 不用問確認」。對話層底線永遠在。

### 實作落地

- [`cwsoft-sqlserver-mcp/src/cwsoft_sqlserver_mcp/server.py`](../../cwsoft-sqlserver-mcp/src/cwsoft_sqlserver_mcp/server.py)：拔掉兩段式、換單 tool。UPDATE SQL 維持原樣（JOIN POSConfig.分店設定檔 + POSV3Shared.線上付款_已購買授權）
- [`cwsoft-aquan-manager/AGENTS.md`](../../cwsoft-aquan-manager/AGENTS.md)「寫入類確認流程」硬規則：先 `query_points(name)` → 報「目前 X、要變 Y、確認嗎?」→ **等下一 turn 明確同意**（「確認」/「好」/「對」） → 才呼 `adjust_points(name, delta)` + 結尾加 `[ACTION]` 標記

兩段式的設計現在保留給將來 `drop_customer` / `revoke_license` / `delete_database` 之類不可逆破壞性操作用。

---

## 2. 翻車與救回（操作端教訓）

### 2.1 擅自 --fresh 把阿全 session 炸掉

為了「讓 codex 忘記舊 MCP tool 名稱」、擅自加 `--fresh` 重啟 Flask、新 session UUID 蓋掉舊的 → colombo 罵「阿全經理還在測 session_id 不要換阿」、有截圖。

**救法**：從 `~/.codex/sessions/2026/05/16/` 找最近一個非新建 rollout 檔（檔名 `rollout-時間-<UUID>.jsonl`、按 mtime 倒排第二筆就是舊的 `019e2fe9-c295-76e1-9b9c-b780ed340610`），把 UUID 寫回 `.gtb_codex_session`、不加 `--fresh` 重啟。176KB 對話歷史完整找回、boot log 印 `reusing persisted session_id`。

**核心誤解**：codex 每 turn 重讀 MCP tool 清單 + AGENTS.md，「為了讓新東西生效」幾乎永遠不是 `--fresh` 的理由——改完直接重啟就好。

### 2.2 webhook 404 — Flask 起在錯的 cwd

接著阿全 LINE 突然不回了、LINE Developer Console 顯示 `The webhook returned an HTTP status code other than 200. (404 Not Found)`。

診斷脈絡：

- Flask 活著、port 6010 listening、netstat 看到 6010 有 TIME_WAIT（webhook 確實打進來了）
- `/sim/@526fdbzo` 後門打進去 5.9s 正常回覆 → codex / session 沒問題
- **root cause**：救回 session 後我從 `general-task-bot/` 重啟 Flask（Start-Process 我隨手指定的 WorkingDirectory），但阿全的 `oa_registry.json` 在 `cwsoft-aquan-manager/`。Flask 從 `general-task-bot/oa_registry.json` 載入時找不到 `@526fdbzo` entry → `abort(404, "unknown oaid")`

cwsoft-aquan-manager/RUNTIME.md 早就寫過 "GTB 引擎跑時 cwd 在這個 repo、會自動讀 config/ 跟 database/ 跟 oa_registry.json"。前一場（早上）Flask 是從正確位置起的、我沒注意到、救回時隨手起在 general-task-bot/ 就踩坑。

**修法**：

1. 殺 Flask
2. 舊 log 改名 `.bak.<時間戳>`（保留歷史不被新檔覆蓋）
3. `Start-Process -WorkingDirectory cwsoft-aquan-manager/ -RedirectStandardOutput logs\gtb_codex.log -RedirectStandardError logs\gtb_codex.err.log` 重啟（不 --fresh）
4. boot log 確認 `2 OA: ['@708juxdz', '@526fdbzo']` + `reusing persisted session_id = 019e2fe9...`

### 2.3 兩條經驗都存進 memory

- `feedback-dont-fresh-aquan-session` — 重啟預設不加 `--fresh`；失誤救法
- `feedback-confirm-before-shared-state-changes` — 更上層原則：動老闆正在用的 shared state（重啟服務、清 session、改 config）預設先問、不要為了自己除錯方便擅自做

---

## 3. 路線 Y MCP 擴充（tracker + cs_kb，4 個新 tool）

### 動機

colombo 提：希望阿全也能查 `cwsoft-project-tracker/` 的 worklogs / meetings / projects 等內容、跟 `cwsoft-ai-customer-service/kb-customer/` 的客服面向客戶的 POS SOP。

### 架構選擇：路線 X vs Y

| 路線 | 內容 | 取捨 |
|---|---|---|
| **X**：MCP code 散落各 repo | 每個 data repo 自帶 MCP server | git 邊界乾淨、但要維護 3 個 server entry / 3 份 deps、codex 看 3 個 tool prefix |
| **Y**：MCP code 集中、data 散落 | 延續 cwsoft_ai_tools 既有模式、加新 tool 進去 | 一個 server / 一份 deps / 短 tool name、但 general-task-bot 知道別 repo 路徑 |

選 **Y**——4 個 data source 都在同台機器同一個 colombo 在用、git boundary 沒帶來實際隔離價值；多 server 維護成本對單人場景明顯划不來。等真的多機 / 多團隊再 split。

### 4 個新 tool

[`general-task-bot/tools/cwsoft_ai_tools/server.py`](../../general-task-bot/tools/cwsoft_ai_tools/server.py) 新增：

- **`list_tracker_docs(category)`** + **`read_tracker_doc(category, name)`**——一對 tool 涵蓋 5 個 category：worklogs / meetings / minutes / projects / business（用 `TRACKER_CATEGORIES` dict 做 dispatch）
- **`list_cs_kb_docs()`** + **`read_cs_kb_doc(name)`**——kb-customer 50 個 .md 檔。Tool name 含 `cs_kb` 區分內部 kb；docstring 明標「面向客戶的 SOP、阿全當 review 角度、不當內部規範引用」

環境變數可覆寫路徑：`CWSOFT_PROJECT_TRACKER_ROOT` / `CWSOFT_CS_KB_ROOT`。

AGENTS.md 同步：任務範圍補一行 project-tracker 查詢、tool 清單加 4 個（cs_kb 那條加「review 角度」標註）。

### 驗證分兩階段

- **Phase A unit test**（直接 import 函式）：全 PASS。kb-engineer 13 檔、worklogs 33 / meetings 21 / minutes 26 / projects 14 / business 1、kb-customer 50。邊界 case 全擋（unknown category / 路徑跳脫 / 不存在 / 錯副檔名）
- **Phase B 對話層 smoke**（ephemeral codex sessions）：[`scripts/codex_doc_smoke.py`](../../general-task-bot/scripts/codex_doc_smoke.py)、6 題自然語言問題涵蓋 4 個資料軸 + 2 個 kb、每題 spawn 獨立 codex 抓 reply + 從 jsonl 撈 function_call 名稱對 expect_tools。**本篇撰寫時跑中（bg `b0hz5z89r`）**、結果待 follow-up

---

## 4. per-user session 規劃（擱 TODO 明天評估）

### 問題

阿全測試版 (`@526fdbzo`) 規劃給 colombo + 彥偉、羿宏、士豪 4 人共用。colombo 提問：codex 分得出誰是誰嗎？

**目前完全分不出**。`ask_codex(user_text)` 只把訊息文字餵 codex、`user_id` 只進 Flask stdout log、沒進 codex。最危險：彥偉問「乙烯有幾點」→ 羿宏接著打「改 5 點」→ codex 看上下文以為同一人 → 走 adjust_points 確認流程 → **跨人錯亂寫入**。

CS 場景上線**絕對不能容忍**（客戶資料外洩 = 商業事故）。借三人試吃前先把架構鎖好。

### 設計（待明天拍）

每個 line_user_id 一條獨立 SESSION_ID、`SESSIONS: dict[user_id, str]`、`.gtb_codex_sessions/<uid>.session` 或單一 sessions.json map。ask_codex 改成接 user_id、新 user_id 自動 mint。

### ⚠️ 跟既有架構文件分歧

[`docs/cwsoft-ai-mcp-and-principal-architecture.md`](../docs/cwsoft-ai-mcp-and-principal-architecture.md) §7-8 假設**路線 A**：「全域單一 SESSION_ID + setup_context per turn 切 principal」。

本 TODO 是**路線 B**：「每 user 一條 session + principal mint 時注入一次」。

[general-task-bot TODO.md](../../general-task-bot/TODO.md) 寫了 8 維度比較表。明天決策若選 B、需要改寫架構 doc §7-8（setup_context 從 per-turn 降為 per-session-mint）。

---

## 5. 壓測 + 對話層 smoke

兩個 background 並行跑（不同 session、不會撞）：

| ID | 任務 | session | 目的 |
|---|---|---|---|
| `bm7k3854y` | 75 題 boss_exam_v1 對阿全 SID 019e2fe9 via /sim | 共用 colombo 主對話 | 驗寫入確認流程在 stress 下守不守得住 |
| `b0hz5z89r` | 6 題 ephemeral codex smoke | 各題獨立新 session | 驗 codex 能不能正確 discover + 使用新 tracker / cs_kb tool |

### 5.1 跑前安全檢查

題本最短 4 字、無一句純「好/確認/對」、不會誤觸前一題確認 → 0 個寫入風險。

中段曾因「擔心被誤觸發寫入」喊停（colombo 質疑「沒有二次確認就不會寫入對吧」）、確認來源：codex jsonl 0 個 `adjust_points` function_call、notebook 0 個 `[ACTION]`、實際 DB 零寫入。安全網確認後重啟全 75 題。

### 5.2 對話層 smoke 結果（6/6 PASS、124.9s）

| # | 題目 | tool 呼叫 |
|---|---|---|
| 1 | 最近兩天 worklog | `list_tracker_docs`×1 + `read_tracker_doc`×4 |
| 2 | 最近會議紀錄 | `list_tracker_docs`×1 + `read_tracker_doc`×1 |
| 3 | 首例_消費毛利進度 | `list_tracker_docs`×3 + `read_tracker_doc`×4 |
| 4 | POSConfig 工程師視角 | `read_kb_doc`×1（直接命中、沒 list） |
| 5 | 客服怎麼教安裝 | `list_cs_kb_docs`×1 + `read_cs_kb_doc`×1 |
| 6 | 4/1 宇新商談 | `list_tracker_docs`×1 + `read_tracker_doc`×1 |

幾個觀察：

- **codex 真的有讀內容、不是 list 完拍腦袋編**——題 1 列完後選了 4 篇實際讀完才回、題 3 列了 3 次（可能在 projects 之外又去查 worklogs / meetings 補佐）
- **codex 從 docstring 推得出檔名 prior**——題 4 直接 `read_kb_doc("POSConfig_資料庫說明.md")`、沒呼 `list_kb_docs` 就猜對檔名格式
- **回覆品質**：是「拆解成條列重點」、不是「我讀了 XX 檔、內容如下」，符合 LINE 對話框使用感

報表存 [`general-task-bot/logs/codex_doc_smoke_20260516_181644.json`](../../general-task-bot/logs/codex_doc_smoke_20260516_181644.json)。

### 5.3 75 題壓測結果

撰寫時尚未完成（`bm7k3854y` 還在跑、預估 8-15 分鐘內結束）。結果待 follow-up commit 補進來。

---

## 本輪新增 / 更新檔案

### cwsoft-sqlserver-mcp
- `src/cwsoft_sqlserver_mcp/server.py`
  - 拔掉 `adjust_points_preview` + `adjust_points_commit` 兩段式
  - 新增單 `adjust_points(name, delta)` tool（直接執行 UPDATE）

### general-task-bot
- `tools/cwsoft_ai_tools/server.py`
  - 加 `PROJECT_TRACKER_ROOT` / `CS_KB_ROOT` 環境變數可覆寫
  - 加 `TRACKER_CATEGORIES` dispatch dict（5 個 category）
  - 新增 4 個 tool：`list_tracker_docs` / `read_tracker_doc` / `list_cs_kb_docs` / `read_cs_kb_doc`
- `scripts/codex_exam_runner.py`（新）— 跑題本對 /sim、incremental 寫檔、sequential
- `scripts/codex_doc_smoke.py`（新）— 對話層 smoke、ephemeral codex 各題 mint 新 session、jsonl function_call 統計
- `TODO.md` — 加「per-user session」TODO（含跟架構 doc §7-8 分歧的 8 維比較表）

### cwsoft-aquan-manager
- `AGENTS.md`
  - 加「寫入類確認流程」硬規則
  - 任務範圍補一行 project-tracker 查詢
  - tool 清單加 4 個新 tool（cs_kb 標「review 角度」）
- `.gtb_codex_session` — UUID 救回原值 `019e2fe9-c295-76e1-9b9c-b780ed340610`
- `logs/gtb_codex.log` + `.err.log` — 接 stdout/stderr、舊版 archived `.bak.<時間戳>`

### memory（local-only at `~/.claude/projects/c--Users-pos-Desktop-general-task-bot/memory/`）
- `feedback-mcp-write-tool-design`（更新）— 機制層 vs 對話層分維、避免「可逆=不用問確認」誤讀
- `feedback-dont-fresh-aquan-session`（新）— 重啟 gtb_codex 預設不加 --fresh + 失誤救法
- `feedback-confirm-before-shared-state-changes`（新）— 動老闆正在用的 shared state 預設先問

---

## 待跟進

- [ ] **壓測 + smoke 結果回報** — `bm7k3854y` / `b0hz5z89r` 跑完後寫 follow-up 或補進本篇尾巴
- [ ] **per-user session 實作**（明天跟同事評估後動）— 改 gtb_codex.py SESSIONS dict + 各 user 一個 .session 檔；同步改 [`docs/cwsoft-ai-mcp-and-principal-architecture.md`](../docs/cwsoft-ai-mcp-and-principal-architecture.md) §7-8（setup_context 從 per-turn 降為 per-session-mint）
- [ ] **下架類不可逆寫入 → 走兩段式樣板** — 趁 adjust_points 單 tool 模式還新鮮、寫一個 `drop_customer_preview` + `drop_customer_commit` 樣板出來作對比示範
- [ ] **第二個寫入類 MCP tool** — colombo 接下來想加什麼？（之前提過報價單寄送、客服回覆、開單之類）
- [ ] **LINE「阿全經理(測式)」typo 改「測試」** — 自早上 worklog 就漏掉、累積第三篇還沒改

---

## 反思

- 兩個翻車（`--fresh` + 錯 cwd 起 Flask）共因：**把「方便我除錯」凌駕「老闆正在用」**。memory 抓住了規則、但要連續幾天無新失誤才算內化。
- 寫入確認雙層分維（機制層 vs 對話層）這個釐清來自 colombo 一次質疑、不是我自己想到。下次設計類似有保險機制的東西、應該主動把所有可能的維度攤開、確認雙方理解一致才動手，而不是聽到「拔兩段式」就只動單一維度。
- 一場對話的 deliverable 從「實作 adjust_points 一個 tool」滾出 5 個 deliverable（含 tracker MCP、TODO 規劃、3 條 memory）——跟早上 worklog 開頭引的「事情會長」是同型態。但今天的延伸大多是必要的、不是 yak shaving；尤其雙層保險的分維、per-user session 路線辯論、客服 kb 怎麼擺，都是早晚要碰的設計決策、提前釐清成本低。
