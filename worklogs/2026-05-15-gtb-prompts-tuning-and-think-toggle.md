# GTB prompts few-shot 改進 + reasoning 模型 think-toggle + v5 baseline matrix

- 日期：2026-05-15
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-opus-4-7)
- 相關專案：general-task-bot、cwsoft-aquan-manager

---

## 討論摘要

### 1. corpus v3 → v5：再修一輪 + 釐清「下個月開始 = 這個月到期」schema 設計

**背景**：5/13 worklog 已交完一輪 v3 baseline（gemma3:4b LLM cascade 77.3% Both）。
過程中我把「id 2/10/11 用了 mission 沒有的 `start_month` 欄位」歸類為 corpus bug。

**colombo 釐清的 schema 設計**：
> 「『這個月到期』和『下個月開始』這兩個可以說是互相依賴的、所以我只設了 due_month。」

換句話說，generate_quote 的 schema **只用 `due_month` 描述時間**——不需要 `start_month`，因為「老闆說下個月開始」內部一律換算成「這個月到期」。
之前 corpus 殘留 `start_month` 是改題本時手快忘了同步換算。

**修法**（`scripts/exam_v4_patch.py`）：
- id 2/10/11：`start_month=12` 移除、`due_month=2025/11`（「12 月開始 → 11 月到期」）
- 規則：`due_month = start_month - 1 個月`（若 M=1 則年份 -1、月份=12）

**rescore 結果**：分數沒變——因為 `rescore_v2.py` 用 user_text 對齊舊 results，
而 dict 的最後一筆 expected 早就是符合慣例的 due_month，等於這幾題之前就被 dict 別名擋掉。
這次 patch 主要是修**檔案內部一致性**——剩下的 fail 就純粹反映 LLM 真實弱點了。

---

### 2. 對 generate_quote 三個 extractor 加 few-shot

**背景**：盤點 gemma3 v3 失敗 17 題，分類後發現有 3 個 prompt 層的系統性問題：

| 問題 | 受影響題數 | 例子 |
|---|---|---|
| `include_tax` 漏抽「未稅」→ N | 7 題 | 全部 `...未稅` 句尾被歸 null |
| `get_charge_months` 把序數月當期數 | 5 題 | 「二月」→ 2、「12 月」→ 12 |
| `start_to_due_month` 年份算錯 | 2 題 | 「3 月開始」→ 2025/03 而非 2026/02 |

**修法**：`config/prompts_pos_dev.ini` 三個 extractor 都加 5-7 個 few-shot 範例，
而不是只給「規則描述」。範例包含 boss 真實會說的句型（「12 月起算六個月」「下一期」「未稅」等）。

特別在 `start_to_due_month` 加一條：「若所述月份在 reference 月之前，預設為 reference 年（不要往未來年份猜）」——
讓 reference=2026-05 時，「12 月起算」→ start=2025/12 而不是 2026/12。

**v5 LLM cascade 實際提升**：
- gemma3:4b：77.3% → 78.7%（+1.4）
- qwen2.5:7b：73.3% → 74.7%（+1.4）
- qwen3.5:2b：53.3% → 57.3%（**+4.0**，小模型對 example 反應最大）

提升比預期小（原本估 +5-10%），主要原因：
- match_pool 拼音 bug（影響 4 題）—— prompt 修不到，是程式 bug
- name 抽取真的錯（id 4「想想」、id 35「有支手機」）—— prompt few-shot 沒覆蓋這類短 keyword

---

### 3. reasoning 模型 think 旗標自動切換：cascade=False / agent=True

**colombo 直覺**：「有思考模式的 LLM 套上 agent mode 應該要打開思考模式，LLM 模式再關掉」。

理由講得很清楚：
- LLM cascade 的每個 extractor 任務超單純（選 enum 或抽 1 個值），思考一輪是 overhead
- agent mega-prompt 要從 22 個任務挑 1 個 + 抽複雜欄位，**這正是「需要思考」的場景**

**實作**：
- `call_home_ollama(prompt, model, timeout, think=False)` 加 `think` 參數
- `call_provider(...)` 加 `**kwargs` 把 provider 專屬參數（含 think）forward 下去
- `agent_classify_and_extract` 自動偵測模型名是否為 reasoning model（白名單 `qwen3` / `deepseek-r1` / `gpt-oss`），
  決定 think=True 或 False 傳給 call_provider

**關鍵踩坑**：
原本以為「`think=True` 對非 reasoning 模型是 no-op」是錯的——
實際上 **Ollama 對非 reasoning 模型送 `think:true` 直接回 HTTP 400**（"gemma3:4b does not support thinking"）。
第一次跑 gemma3:4b agent v5 直接 0/75 全錯就是這原因。
修法用白名單只對 reasoning 模型開 think，其他模型完全不傳這個 flag。

**反向驗證 colombo 的直覺**：

| qwen3.5:2b Agent | think=false（v3） | think=true（v5） | 變化 |
|---|---|---|---|
| Intent | 73.7% | **93.3%** | **+19.6** |
| Both | 33.3% | 42.7% | +9.4 |
| 耗時 | 4 min | **137 min** | 慢 34 倍 |

開思考確實救回 intent 分類大段，但 Both 只 +9.4——
因為 Q2 欄位抽取部分還是受同樣的 prompt schema 限制（agent 是 mega-prompt 模式，沒辦法用 cascade 那邊改的 few-shot），
而且時間成本爆炸。**reasoning 模型對 agent 有幫助、但仍不是 GTB 的最優解。**

---

### 4. v5 完整 baseline matrix（75 題 corpus）

| 排名 | 配置 | Intent | Values | **Both** | 耗時 |
|---|---|---|---|---|---|
| 🥇 | **gemma3:4b · LLM cascade** | **97.3%** | 80.0% | **78.7%** | **4.6 min** |
| 🥈 | qwen2.5:7b · LLM cascade | 96.0% | 76.0% | 74.7% | 5.5 min |
| 🥉 | codex_cli (gpt-5.4) · Agent | 90.7% | 68.0% | 66.7% | 19.2 min |
| 4 | qwen3.5:2b · LLM cascade（think=false）| 93.3% | 60.0% | 57.3% | 4.6 min |
| 5 | gemma3:4b · Agent | 60.0% | 50.7% | 45.3% | 4.3 min |
| 6 | qwen3.5:2b · Agent（think=true）| 93.3% | 44.0% | 42.7% | **137 min** |
| 7 | qwen2.5:7b · Agent | 76.0% | 41.3% | 40.0% | 4.7 min |

**核心結論不變**：
- gemma3:4b LLM cascade 仍是冠軍（vs 上次 v3）
- 對比 codex agent：準確率 +12.0、速度 4.2 倍
- 一台 RTX 2060 + 開源 4B + cascade = 比花錢 codex agent 更好

---

### 5. ops 踩坑：長時間 agent 跑題會把 SSH tunnel 拖斷

**事件**：qwen3.5:2b agent + think=true 跑了 137 分鐘（~2h17min），跑完之後 SSH tunnel（pid 361028）就斷了。
home 機器本身沒事（hostname / ollama 都還在），是 work 端的 ssh 連線斷了。

可能原因：
- Windows OpenSSH 對長時 idle / 大流量 ssh 連線有 server-side timeout
- 雖然啟 tunnel 時設了 `ServerAliveInterval=30 ServerAliveCountMax=3`、`ExitOnForwardFailure=yes`，
  但 reasoning 模型每個請求耗時 100 秒+、可能某次 keep-alive 失序

**症狀**：
- runner 還能跑（每題回 `agent Q1 failed: tunnel down` errors）
- ollama 端 `api/ps` 顯示 `{"models":[]}` ——其實 home 那邊 ollama 是正常的、是 tunnel 不通
- 重啟 ssh tunnel 後一切恢復

**短期 mitigation**：每跑完一輪測試確認 tunnel 狀態（`curl localhost:11434/api/tags`），
真斷掉就重啟（不影響 Flask、不影響 agent 結果）。

**長期解法（待跟進）**：
- 改 autossh 自動重連（autossh -M 0 ...）
- 或在 `call_home_ollama` 加「ConnectionError 自動重啟 tunnel」邏輯
- 或在 home 端架反向 tunnel 主動推

---

## 本輪新增 / 更新檔案

### general-task-bot
- `gtb_dev.py`
  - `agent_classify_and_extract` 加 `think_capable` 模型白名單偵測，自動傳 `think=True/False` 給 call_provider
- `llm_clients.py`
  - `call_home_ollama` 加 `think: bool = False` 參數
  - `call_provider` 加 `**kwargs` 把 provider 專屬選項（目前只有 think）forward 下去
- `scripts/exam_v4_patch.py`（新）：corpus id 2/10/11 把 start_month 換成 due_month=2025/11

### cwsoft-aquan-manager
- `config/prompts_pos_dev.ini`
  - `include_tax`：8 個 few-shot 範例
  - `get_charge_months`：8 個範例 + 強調「序數月不算期數」
  - `start_to_due_month`：7 個範例 + 補「過去月份預設今年」規則
- `benchmark/boss_exam_v1.json`：3 題 schema 修正（76 → 75 題，含上輪移除 id 61）
- `benchmark/reports/2026-05-15_*`：v5 sweep 7 個 baseline 結果資料夾

---

## 待跟進

- [ ] **gtb_dev.py 切 PROVIDER=home_ollama / LLM_MODEL=gemma3:4b 當預設**——v5 數字確定夠強，可以正式上 dev default
- [ ] match_pool 拼音 bug（4 題卡「正欣」吸鐵）：修 `calculate_phonetic_similarity` 或 customerlist 重排優先順序
- [ ] LLM cascade 剩餘 fail（gemma3 共 16 題）裡面，5 題 LLM 真實抽錯需要更精準的 prompt（id 4「想想」、id 35「有支手機」、id 60 paper 多行黏一起、id 64 typo「未遂」、id 22「更新客戶」）
- [ ] SSH tunnel 長時間斷線 mitigation：autossh / 自動重啟 / home 端反向 tunnel 三選一
- [ ] reasoning 模型走 agent 雖然 intent 衝高、但時間成本是 cascade 的 30 倍——除非 agent 真的有「multi-step / tool use」場景需要，否則生產上不適用
- [ ] 既然發現 home 多了 `deepseek-r1:7b` 模型，下次補測 deepseek-r1 LLM cascade（也是 reasoning 模型，think 自動關）跟 agent（think 自動開）
- [ ] prod gtb.py 換 LLM provider（等 dev 版穩定跑一陣子之後）
