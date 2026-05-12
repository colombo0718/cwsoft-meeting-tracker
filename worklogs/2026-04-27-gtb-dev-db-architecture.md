# GTB Dev：通用資料庫架構實作 + 信心值機制完工

- 日期：2026-04-27
- 參與者：colombo0718 × Claude (claude-sonnet-4-6)
- 相關專案：general-task-bot、cwsoft-aquan-manager

---

## 一、本次完成的事項

### 1. db_helper.py 新增（通用資料庫層）

實作完整四張表架構，所有 SQLite 操作集中在此，gtb_dev.py 不直接寫 SQL。

**管理的 DB：**
- `config.db`：user registry（oaid + user_id → conv DB 路徑）
- `conv_{user_id}.db`：四張表

**四張表：**

| 表 | 職責 |
|----|------|
| `message_log` | 每則進出訊息流水，含 session_id / direction / content_type / role |
| `clarification_log` | 澄清狀態機，pending → resolved/cancelled，含 context_json 儲存流程快照 |
| `corrections` | 使用者確認過的名稱勘誤對應，下次直接命中 |
| `decisions` | 決議紀錄，取代 human_check 的 in-memory 狀態 |

**message_log 的 role 欄位設計：**
- `in`：claim / answer / confirm / cancel / query / unknown
- `out`：result / clarify / confirm_request / draft / error

**clarification_log 加入 `context_json`：** 儲存 task_id、values、run_at、raw_input，讓 pending → resolved 後能繼續主流程。

**逾時機制：** pending 超過 5 分鐘（`CLARIFICATION_TIMEOUT_SECONDS = 300`）自動 cancel，避免 stale 狀態把下一則訊息誤吃成澄清答案。

---

### 2. gtb_dev.py 重構

**移除：**
- `todo_command` 全域 dict 完全移除
- `generate_groq_reply` / `generate_openrouter_reply` / `generate_huggingface_reply` / `generate_remote_worker_reply` 四個函數刪除
- 重複的 API key 讀取（移交給 llm_clients.py）
- `from huggingface_hub import InferenceClient`、`FlexMessage` 等 unused import

**新增 / 改動：**
- `import db_helper`、`from llm_clients import call_provider`
- `CONFIG_DB_PATH` 初始化，啟動時建立 config.db
- `llm_complete` 改為三行 thin wrapper：`call_provider(PROVIDER, user_text, LLM_MODEL).text`
- 全流程改用 DB-backed 狀態機：
  - 澄清狀態 → `clarification_log`（重啟存活）
  - human_check 等待確認 → `decisions`（state='awaiting_confirmation'）
  - 每則進出訊息 → `message_log`
  - 澄清確認後 → `corrections`

**澄清分支邏輯修正：**
- 使用者自由輸入（不是 1/2/3，也不在選項中）→ 直接採用，存入 corrections
- 修前：自由輸入會被 `resolved = None` 吃掉，再問一次

---

### 3. llm_clients.py 正式接入

`llm_clients.py` 已有完整的 `call_provider(provider, prompt, model)` 介面，回傳 `LLMResult`（ok / text / latency_sec / error）。gtb_dev.py 現在統一走此層，支援 groq / openrouter / hf / remote_worker / codex_cli / gemini_cli。

---

### 4. 拼音相似度問題討論

**現象：** 使用者打「林一」，top-3 選項出現「立亞/鑫罄/拾易」，完全沒中。

**根本原因：**
- 「零壹通訊行」在清單裡，但名稱比「林一」長很多
- 拼音比對 ratio = 2 × 匹配字元 / (短字串 + 長字串)，長候選分母大，被稀釋
- 「立亞」等短名稱分母小，相似度反而排得更高

**討論結論：** 這類「林一 → 零壹通訊行」的對應，靠相似度演算法一次推出不現實。**由 corrections 勘誤表來學習和記憶**，使用者確認一次後永久記住。`lookup_correction` 已在 db_helper.py，待接進 `gather_fields`（下次做）。

---

### 5. 雜項

- `gtb_dev.py` 亂碼整理：docstring、shadow mode 區段 comments、`parts.append` 的使用者訊息 label 全部修正為正確繁中

---

## 二、架構決策紀錄

**Q：DB 設計會不會太重、太冗餘？**

結論：不重。SQLite 幾乎零開銷，4 張表的分工不重疊。`role` 欄位讓腳本/agent 能精確過濾對話歷程，成本僅是每行多一個字串。分批做的方案被否決——架構既然出來，就一次到位。

**Q：`decisions` vs `todo_command`**

`todo_command` 是純 in-memory dict，重啟即消失。`decisions` 持久化到 DB，human_check 狀態跨重啟存活，且有完整的歷史紀錄（state 機器：awaiting_confirmation → queued/executed/cancelled）。

---

## 三、尚未完成的事

- `lookup_correction` 尚未接進 `gather_fields`（勘誤查找還沒啟用）
- 相似度低分過濾（候選分數低於 0.4 不觸發澄清）尚未套用
- `decisions` 表的完整測試（human_check 流程端對端）
- `corrections` 實際命中測試（需等下次「林一」再傳）
