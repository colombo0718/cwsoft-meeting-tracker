# GTB × 小豪數位分身導入與接線整理

- 日期：2026-04-14
- 主機：公司主機
- 參與者：colombo0718 × Codex (gpt-5.4)
- 相關專案：general-task-bot、digital-agent-xiaohao、cwsoft-linebot-service

---

## 討論摘要

### 1. 小豪定位與 GTB 架構保留

**結論：** 小豪定位為「數位分身代理」，不是低階客服 chatbot；GTB 架構保留，因為需要它的需求判斷與 prompt/context 調度能力。

補充要點：
- 小豪目標場景：工作匯報、專案備詢、新想法討論、待辦整理
- 不急著做：直接執行高風險 API、未確認就寫正式 TODO

---

### 2. codex_cli 併入 LLM 後端統一層

**結論：** `codex_cli` 已接進 `llm_clients.py`，可用 `call_provider("codex_cli", ...)` 走同一介面；benchmark 顯示可用但延遲偏高。

補充要點：
- `codex_cli` 先作為候選 backend，不取代 GTB 主流程
- 仍需在小豪專案設定預設 provider/model

---

### 3. Gemini CLI 先暫緩

**結論：** Gemini CLI 安裝完成，但出現 429 容量問題；先暫不列為主力 backend。

---

### 4. 小豪專案骨架與路由打通

**結論：** `digital-agent-xiaohao` 專案已建立骨架，Caddy 路由與 webhook 已打通。

補充要點：
- Caddy 前綴：`/xiaohao/*` → `127.0.0.1:6006`
- webhook 必須包含 `oaid`：`/xiaohao/callback/<oaid>`
- `oa_registry.json` key 與 `<oaid>` 必須一致

---

## 本輪新增 / 更新文件

### digital-agent-xiaohao

- `README.md`
- `PROJECT.md`
- `TODO.md`
- `oa_registry.json`
- `customerlist.txt`
- `config/mission_xiaohao.json`
- `config/prompts_xiaohao.ini`
- `database/.gitkeep`

### general-task-bot

- `llm_clients.py`（新增 `codex_cli`、`gemini_cli` adapter）
- `scripts/llm_benchmark.py`（補 `codex_cli`、`gemini_cli` 預設模型）

### mine-meeting-room

- `CONVENTIONS.md`（Header 改為 `相關專案`）
- `PROJECT.md`（補「讀專案順序」說明）
- 舊會議記錄 header 統一更新為 `相關專案`
- `meetings/2026-03-25-thesis-workflow-and-timeline.md` 內容復原

---

## 待跟進

- [ ] 設計小豪專案的預設 provider/model（專案級設定 + 啟動參數覆蓋）
- [ ] 小豪切換為 `codex_cli` 作為實際回覆後端（保留 GTB 架構）
- [ ] 確認 `6006` 啟動流程與基本回覆測試
- [ ] 決定待辦落地位置（小豪專案 / mine-meeting-room / 各專案 TODO）
