# MCP server MVP 上線 + capability 鎖死 + AGENTS.md instruction + GTB 角色重新定位

- 日期：2026-05-16
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-opus-4-7)
- 相關專案：general-task-bot、cwsoft-aquan-manager、跨專案

> 接續同日 `2026-05-16-gtb-codex-line-bot-and-mcp-architecture.md`（早上）。
> 早上把架構規劃寫完、下午照規劃實作 step 1+2、過程中又拉出來談 GTB 角色定位。

---

## 討論摘要

### 1. MCP server MVP 寫完上線（架構 doc 的 step 1+2）

**內容**：`general-task-bot/tools/cwsoft_ai_tools/server.py`，30 行 + FastMCP SDK，2 個唯讀 tool：

| Tool | 用途 | 安全設計 |
|---|---|---|
| `list_project_files()` | 列 PROJECT_ROOT 一層、不遞迴、跳過 hidden | 只讀、不能傳 path 參數 |
| `read_doc(name)` | 讀 PROJECT_ROOT 底下 whitelist 內檔案 | name 含 `/` `\\` `..` 直接拒；whitelist 8 個常見 doc 檔 |

PROJECT_ROOT 預設 `cwsoft-aquan-manager`、可用 `CWSOFT_AI_TOOLS_ROOT` 環境變數覆寫。

註冊到 `~/.codex/config.toml`：
```toml
[mcp_servers.cwsoft_ai_tools]
command = "python"
args = ["-m", "tools.cwsoft_ai_tools.server"]
cwd = "C:\\Users\\pos\\Desktop\\general-task-bot"
```

第一次 codex exec 立刻 discover 兩個 tool（看到名字 `mcp__cwsoft_ai_tools__list_project_files` / `read_doc`），證實 step 2 成立。

---

### 2. Capability 鎖死過程：三輪 lockdown + 兩個 Windows-specific 踩坑

#### 踩坑一：MCP discover 通了、但 call 全 fail

第一次驗證：codex 看得到 tool schema，但 `mcp tool started → failed → user cancelled MCP tool call`。
查證後是**跟之前 PowerShell DLL init failed (0xC0000142) 同一個 Windows job-object sandbox bug**——
codex 在 `unelevated` sandbox 裡 spawn 任何子程序都會掛、不分 PowerShell 或 Python MCP server。

唯一能跑通的設定：**`--dangerously-bypass-approvals-and-sandbox`**（OS 沙箱完全關掉）。

#### 踩坑二：「OS 沙箱關掉」聽起來嚇人、但跟我們的設計剛好對齊

colombo 的疑問：「危險嗎？」我的整理：

| | OS 沙箱保護 | tool 安全保護（白名單 / role check / etc.）|
|---|---|---|
| 「正常」設定 | ✓ | △（要寫對）|
| **我們的設定** | ✗（Windows bug 強迫關）| **✓（capability-restricted、codex 只看得到我們批准的 tool）**|

換句話說：我們本來就不靠 OS 沙箱、靠 MCP tool 白名單。OS 沙箱關掉沒影響、Windows bug 反而剛好提示我們「這條路本來就不通、走 MCP-only 才對」。

#### 三輪 disable 把 codex 看得到的工具從 95 個砍到 11 個

```bash
# Round 1: shell_tool 拔掉
--disable shell_tool
# 後果：codex 看不到任何 shell

# Round 2: multi_agent 拔掉
--disable multi_agent
# 後果：spawn_agent / send_input / resume_agent / wait_agent / close_agent 全消失

# Round 3: apps 拔掉
--disable apps
# 後果：~80 個 mcp__codex_apps__github_* 全消失

# 同步在 ~/.codex/config.toml：
[plugins."github@openai-curated"] enabled = false   # 不讓 plugin 重新載
# [mcp_servers.mempalace] 整段注解掉             # 阿全用不到 mempalace
```

**最終 codex 看到的工具清單**（11 個，從 95 剩下）：
- `mcp__cwsoft_ai_tools__list_project_files` ✓ 我們寫的
- `mcp__cwsoft_ai_tools__read_doc` ✓ 我們寫的
- `web.run` ⚠ 沒 feature flag 能拔、靠 prompt 約束
- `apply_patch` ⚠ 同上
- `multi_tool_use.parallel`、`update_plan`、`request_user_input`、`view_image`、3 個 MCP 探索 tool — 無害

**latency 同時大幅降低**：tool schema 從 95 個剩 11 個、codex 處理單訊息從 34s 降到 5-6s。

---

### 3. 第二個踩坑：boot prompt 是 user message、不是 system

第二輪驗證：tool 鎖好了，但 codex 故意要它做沒授權的事情、它老實說「我不能」、**但沒加 `[WANT_NEW_TOOL]` 標記**。
直接戳它「你忘了標記規則嗎」、它回：

> 「不是『沒記住』，是這個對話裡我目前實際生效的指示，沒有要求我必須輸出那些 tag」

**根因**：`gtb_codex.py` 的 `BOOT_SYSTEM_PROMPT` 是當作 codex session 的**第一條 user message** 送進去的、不是真正的 system prompt。後續 exec resume 看它就是「歷史對話」、隨時間褪去權重。

**解**：用 codex **原生 AGENTS.md instruction file 機制**——
- AGENTS.md 是 codex 啟動時自動載入、視為**長效指令**、不會在對話歷史裡稀釋
- 條件：codex 的 working directory 底下要有 AGENTS.md
- 動作：建 `cwsoft-aquan-manager/AGENTS.md`、`gtb_codex.py` mint 時加 `-C C:\Users\pos\Desktop\cwsoft-aquan-manager` 顯式設 codex workdir

`general-task-bot/AGENTS.md` 已經是 VB.NET 程式分析的規則（不要污染），所以新建 `cwsoft-aquan-manager/AGENTS.md` 專為阿全用。

第三輪驗證：fresh session 啟、立刻問「幫我把佳展加 5 點」、回覆乾乾淨淨、最後一行就是 `[WANT_NEW_TOOL] 資料庫加點數的 MCP tool...`。同樣測試 KB_FIX 也準時出現。

---

### 4. 阿全經理 self-report 標記機制（colombo 拍板的 feedback loop）

colombo 的設計 idea：

> 「修改類動作會個別作成一個個 MCP 指令；ai 對 POS 知識理解錯了 / 想要新功能 / 不知道怎麼答 → 用特殊文字標記方便查詢就好。我上班例行檢查這些字串，再判斷怎麼處理。」

四種標記、寫進 AGENTS.md hard-rule：

| 標記 | 觸發情境 |
|---|---|
| `[KB_FIX]` | 使用者糾正 codex 對 cwsoft / POS 的知識 |
| `[WANT_NEW_TOOL]` | 使用者要的事沒有對應 MCP tool |
| `[NEED_INFO]` | 完全不知道答案、也沒工具能查 |
| `[BUG_SIGHTED]` | 看到疑似 bug / 異常 |

**美學**：
- 不需要 codex 主動發 webhook / 寫 DB / 開 issue
- 不需要新 endpoint / 新流程
- colombo 只要 `grep -E "\[KB_FIX\]|\[WANT_NEW_TOOL\]|\[NEED_INFO\]|\[BUG_SIGHTED\]" logs/*_chat.log` 就能集中所有訊號
- 簡單到爆、但對「老闆人工 close-loop」的場景 100% 夠

---

### 5. LINE 上實測：肉眼可見的進步

老闆貼上 LINE 截圖、阿全的回覆：

```
> 你可以看到其他資料夾的東西嗎
目前不行。
我現在能用的只有這個專案內的工具，主要是查 cwsoft-aquan-manager 根目錄有哪些檔案/資料夾、
還有讀部分白名單文件。
專案外的其他資料夾，或這個專案裡更深層的一般檔案，我現在都不能直接看。
[WANT_NEW_TOOL] 查看其他資料夾與任意專案內檔案內容的 MCP tool

> 那你可以幫我查客戶資料庫嗎?
目前不行。
我現在沒有查資料庫的 MCP tool，所以不能直接查客戶資料、會員、點數或 POS 資料表。
[WANT_NEW_TOOL] 查詢客戶資料庫的 MCP tool，可查會員、點數、客戶與 POS 相關資料
```

完美達到設計：
- 簡潔回覆、不解釋技術細節
- 不嘗試走 web.run / apply_patch 旁門
- 自陳標記精準、自然、可 grep
- 老闆評語：「**肉眼可見的大進步**」、「**之前搞半年多的 gtb 系統 幾乎可以丟垃圾桶了**」

---

### 6. GTB vs codex 角色重新定位（這節最重要）

老闆「丟垃圾桶」的直覺很自然——但我刻意拉了一下，因為兩個是**不同產品不是新版淘汰舊版**。

#### 對照

| | GTB（gemma3 cascade）| 阿全（codex + MCP） |
|---|---|---|
| **用途** | LINE 一句話 → 立刻打 API（adjust_points 之類）| LINE → 對話、查、回答、累積上下文 |
| **特性** | 無記憶、無對話、每次重新看 | 有記憶、跨 turn、會自陳缺什麼 |
| **延遲** | 3-5s/題 | 5-15s/題 |
| **成本** | 0（home gemma3:4b 本機 GPU） | OpenAI API token（gpt-5.4） |
| **回應形態** | 簡短結構化、固定格式 | 對話自然、可長可短 |
| **最佳場景** | 老闆連發「鈞凱勝加 12 點 / 睿閎加 1 點...」30 句 | 老闆問「README 講啥、mission JSON 啥結構、能不能列摘要」 |

#### 6 個月不是丟掉

就算 GTB cascade 程式碼最後不跑、**這些資產仍是黃金**：

| GTB 累積 | 在新世界的角色 |
|---|---|
| `mission_pos.json` 22 個任務 + 欄位 schema | 未來各個 MCP tool 的 spec 定義來源 |
| customerlist + 拼音相似度比對 | MCP `search_customer` tool 直接複用 |
| `boss_exam_v1.json` corpus + 多輪校正 | 同一份 corpus 做 codex 版本驗收、不用重發明 benchmark |
| benchmark methodology + matrix 對照表 | 跨 LLM provider 公平比較的 framework |
| `with_confidence=true` 機制 | 未來 MCP tool 內部信心評分也適用 |
| 24 個 extractor prompt（含 few-shot） | LLM cascade 還活著的話直接用；若改成 codex agent 也是「這些是該留意的判斷」的提示 |

#### 兩條可能的劇情

- **劇情 A**（保守）：GTB 從 runtime 變 spec library——程式碼簡化成 mission/customerlist/utils，被 MCP tool import
- **劇情 B**（並行）：兩條路徑都接 LINE、自動分流——「短句帶人名 + 數字」走 GTB、「長對話探索」走 codex
- **劇情 C**（激進）：阿全 + sqlgate-style MCP tool 全面接管、GTB cascade 退役

劇情 B 短期看最務實——重點不是「選哪一個」、是「都留著、各擅勝場」。

#### colombo 的金句

> 「過去半年在 gtb 的思考、也許就是今天想到用這種方式串接 codex 服務的滋糧。」

——這句先記下來。半年的 GTB 摸索（cascade vs agent 大戰、benchmark corpus、信心值機制）是必要的「地基經驗」、沒這些根本想不到「capability-restricted MCP + AGENTS.md hard-rule + self-report tag」這套組合。

---

## 本輪新增 / 更新檔案

### general-task-bot
- `tools/cwsoft_ai_tools/__init__.py`（新，空檔讓 dir 變 package）
- `tools/cwsoft_ai_tools/server.py`（新）：30 行 MVP MCP server、2 個唯讀 tool
- `gtb_codex.py`：
  - `--codex-sandbox` 預設 `danger-full-access`（Windows sandbox + MCP spawn 唯一通解）
  - 加 `--disable-builtin`、預設 `["shell_tool", "multi_agent", "apps"]`
  - mint codex 時加 `-C str(PROJECT_DIR)` 顯式設 workdir → 自動載入該 dir AGENTS.md
  - resume 不傳 `-C`（不收）、workdir 從 mint 時繼承
  - `BOOT_SYSTEM_PROMPT` 補強說明（belt + suspenders、AGENTS.md 是主）

### cwsoft-aquan-manager
- `AGENTS.md`（新）：阿全 codex hard-load 指令——任務範圍、能用 tool、self-report 標記 4 種定義 + 範例

### ~/.codex/
- `config.toml`：
  - `[plugins."github@openai-curated"] enabled = true → false`
  - `[mcp_servers.mempalace]` 整段注解掉
  - `[mcp_servers.cwsoft_ai_tools]` 新增

---

## 待跟進

- [ ] **架構 doc step 3**：`policy.py` + `setup_context` MCP tool + 每個 tool 開頭 `can()` check（principal-based RBAC）
- [ ] **第一個寫入類 MCP tool**：建議從 `adjust_points` 起、接 sqlgate `/adjust_points` endpoint、tool 內部做 owner role check（vip_customer 不該能用）
- [ ] **`principals.json` v1**：先把 colombo 自己一個 owner 寫進去、之後加客戶
- [ ] **抽空收集 LINE 對話**：固定週期 grep `[KB_FIX] / [WANT_NEW_TOOL] / [NEED_INFO] / [BUG_SIGHTED]`、檢查 codex 自陳了哪些需求
- [ ] `web.run` / `apply_patch` 沒 feature flag 能關——除了 AGENTS.md 約束、定期 audit `~/.codex/sessions/.../rollout-*.jsonl` 看 codex 有沒有偷叫
- [ ] gtb_codex.py 加保護：catch 到 codex stdout 含 `apply_patch` / `web.run` 字眼時印警告（soft monitoring）
- [ ] 寫 `scripts/grep_chat_self_reports.py`：把 logs/*_chat.log 裡 4 種標記 dump 成可讀清單
- [ ] 開始考慮劇情 B 的 LINE 訊息分流邏輯（要哪一支進 GTB cascade、要哪一支進 codex）
- [ ] 還有 LINE OA 名字「阿全經理(測式)」typo 沒改（早上 worklog 也提過）
