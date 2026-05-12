# GTB 解耦進展 × 信心值機制 × 測試基建會議（完整版）

- 日期：2026-04-14
- 主機：公司主機
- 參與者：colombo0718 × Codex (gpt-5.4)
- 相關專案：general-task-bot、cwsoft-aquan-manager、cwsoft-ai-customer-service、mine-meeting-room

---

## 討論摘要

### 1. GTB 核心定位與專案解耦

本輪確認並持續推進：

- GTB 是共用核心，不是阿全專案的內嵌腳本集合。
- 各 chatbot 專案需獨立資料夾，攜帶自己的 `config/`、`database/`、`oa_registry.json`、相依檔。

已落地重點：

- 新建阿全專案：`C:\Users\pos\Desktop\cwsoft-aquan-manager`
- 已建立/搬入：
  - `config/`、`database/`、`README.md`、`oa_registry.json`
  - `mission_pos.json`、`prompts_pos.ini`
  - `customerlist.txt`、`generate_customerlist_simple.py`
  - `database/todo_list.db`

---

### 2. 阿全特化殘留清理

決策：

- GTB 核心保留「相依檔讀取」能力，不負責「相依檔生成腳本」執行。

已完成：

- `gtb.py` 的 `match_pool` 去特化，改為通用讀取 `PROJECT_DIR/<pool_file>`。
- 移除 `gtb.py` 內自動執行 `generate_customerlist_simple.py` 的行為。
- `subprocess` 在 `gtb.py` 不再需要。

結論：

- `customerlist.txt` 是阿全專案相依檔，保留在專案內。
- 名單更新週期由阿全專案自己排程，不綁在 GTB webhook 主流程。

---

### 3. todo worker 內嵌與排程閉環

需求背景：

- 每個專案拆分後，排程應自動跟著專案 DB 走，不能再靠全域 worker。

已完成：

- `gtb.py` 內嵌 todo worker。
- 啟動 GTB 時自動啟 worker，巡查該專案 `database/todo_list.db`。
- 加入 `WERKZEUG_RUN_MAIN` 判斷，避免 debug reloader 重複啟 worker。

已知限制（仍待補強）：

- 當前 worker 對失敗重試與狀態機仍偏簡化。
- `run_at` 異常值與 `pending` 重試風險仍存在。

---

### 4. 高風險事故：下架半套與 pending 重跑

事件重點：

- 曾出現高風險任務仍為 `pending`，被 worker 重新撈起執行。
- 發現 `detach_customer` 類路由 / SP 一旦誤觸，存在半套執行風險（標記停用、刪設定、detach DB 等步驟不一致）。

已做止血：

- 將 `cwsoft-ai-customer-service/database/todo_list.db` 的 `pending` 全改 `done`（8 筆）。
- 將 `cwsoft-aquan-manager/database/todo_list.db` 的 `pending` 全改 `done`（3 筆）。
- 補做 SQL 檢查 `千訊`，確認該次未形成完整下架結果（正式庫仍 online、主檔停用=0）。

決策：

- 高危險指令預警與多重確認列入 GTB TODO（不可再拖）。

---

### 5. 會議理解修正（AI 客服 vs 全葳小幫手）

修正點：

- 有基本知識庫的是 **AI 客服**，不是全葳小幫手。

共識：

- GTB 核心化已進入優化期，不是還在「是否拆分」階段。
- AI 客服後續重點在勘誤閉環、來源追蹤、模擬問答。

---

### 6. 信心值機制設計（config-first）

核心共識：

- 不用先全改 prompt，先讓 config 具備可控開關。
- `classify_tree` 與 `fields` 都可由 `with_confidence` 控制輸出模式。

本輪決策：

- 先採 `with_confidence: true/false`（欄位級與 classify_tree 級）。
- 先取消 `classify_tree` 一律 `true` 的強制，改為可選。
- `answer_mode` 的抽象優點保留，但先只列 TODO，不立即上線。

---

### 7. 風險控管：先做 `gtb_dev.py`，不直接動正式 `gtb.py`

明確決策：

- 因主程式風險高，先分出開發版 `gtb_dev.py`。
- 新機制全部先在 dev 版驗證。

已完成於 `gtb_dev.py`：

- `run_extractor(..., with_confidence=...)`
- 依 `with_confidence` 前置 `format_value_only` 或 `format_with_confidence`
- `classify_tree.with_confidence` 可選
- `fields.<field>.with_confidence` 可選
- 含信心值 JSON 解析與 fallback（格式錯誤不直接炸流程）

---

### 8. 系統模板與 benchmark 基建

已完成：

- `prompts_system.ini` 新增共用模板：
  - `format_value_only`
  - `format_with_confidence`
- 新增 `llm_clients.py`（抽離 provider 呼叫邏輯）
- 新增 `scripts/llm_benchmark.py`（速度 + correct 測試）
- benchmark 已改平行模式（`--max-workers`）

測試觀察（同題組）：

- Groq（`openai/gpt-oss-20b`）速度與穩定度顯著優於 remote_worker 現況。
- remote_worker 模型差異大，且併發過高易 timeout。
- `qwen3.5:2b` 在當前 remote_worker 併發條件下 success/correct 偏低且延遲過高，不適合即時主路徑。

---

### 9. GTB 測試入口方向：脫離 LINE OA

共識：

- GTB 不應被 LINE OA 綁死；需有可離線批測入口。

方向：

- `gtb_dev.py` 增加 CLI/考題本模式（`--cli` / `--exam`）。
- 每個 chatbot 專案自帶 `benchmark/`，存：
  - 題本
  - 小抄（勘誤表）
  - 報告
- 先不拆多層資料夾，靠檔名區分用途。

---

## 本輪新增 / 更新文件

### general-task-bot

- `gtb_dev.py`（新增 confidence 開關與格式模板接線）
- `prompts_system.ini`（新增 `format_value_only` / `format_with_confidence`）
- `llm_clients.py`（新增）
- `scripts/llm_benchmark.py`（新增並升級平行）
- `docs/gtb_專案使用盤點.md`（更新主要專案口徑）
- `docs/下架半套事故整理.md`（事故整理）

### mine-meeting-room

- `meetings/2026-04-14-gtb-confidence-and-benchmark-roadmap.md`（本檔）

---

## 待跟進

- [ ] 在 `gtb_dev.py` 落地 `--cli`（單句測）與 `--exam`（批量題本）模式。
- [ ] 定義 `benchmark/` 檔名規則並完成 parser（題本/小抄/報告）。
- [ ] 在阿全專案挑 2～3 個欄位先開 `with_confidence=true` 試點。
- [ ] 補上高危險任務保護（多重確認、審計、失敗狀態機）。
- [ ] 待 dev 版穩定後，再評估回寫正式 `gtb.py`。
