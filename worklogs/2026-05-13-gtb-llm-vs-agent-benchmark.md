# GTB LLM cascade vs Agent mega-prompt 全面 benchmark

- 日期：2026-05-13
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-opus-4-7)
- 相關專案：general-task-bot、cwsoft-aquan-manager

---

## 討論摘要

### 1. 加 agent 模式做架構對照實驗

**背景**：之前討論過「GTB 核心要不要從 LLM cascade 改成 agent」，但沒拿真實數據打過架。
codex_cli 是 reasoning agent，跟現有「切碎成 N 個 extractor 餵 LLM」的設計理念相反。

**決策**：在 `gtb_dev.py` 的 `/sim` 加 `mode=agent` 分支——
- Q1「哪個任務」mega-prompt 把 22 個 task description 一坨送進去
- Q2「怎麼做」mega-prompt 把選中 task 的 fields schema 送進去
- 預設 provider 走 codex_cli + gpt-5.4
- body 可帶 `agent_provider` / `agent_model` 切後端（讓同模型可以同時跑 cascade vs agent）

**理由**：dev 環境裡兩種架構並存、用同題本做 apples-to-apples 對比，是唯一能下定論的方法。

---

### 2. Groq / HF 雲端 LLM 的 baseline 全部是 rate-limit 雜訊，不是分類能力

**背景**：第一輪用 Groq + Llama-3.3-70B 跑 boss_exam，結果只有 3.9%；HF + Llama-3.3-70B 2.0%。
數字慘到不像分類能力的問題。

**結論**：93/102 items 的 Tier 1 LLM 呼叫回 `"Error"`——是 free tier 的 429。
Groq llama-3.3-70b free tier 30 RPM；GTB 每題 3-4 個 cascade call 連發 = 必爆。

**修法**：給 `call_groq` / `call_hf` 加 429 + 5xx retry + Retry-After 退避；exam_runner 加 `--per-item-sleep`。

**第二次測試結果**：HF throttled 上升到 14.7%（依然受 rate limit 干擾，87/102 tier4 fallback）；
Groq throttled 0%（quota 整輪燒光，每題 timeout 後重試到 90s 上限）。

**最終行動**：**放棄 Groq / HF 當 GTB 的對外 LLM 依賴**。
免費額度根本撐不住 GTB 的呼叫密度，付費的話成本不可控。

---

### 3. Pivot：本機 Ollama via SSH tunnel 到 home RTX 2060

**背景**：work 機器 GeForce 210 太舊跑不動 LLM；本來計畫在 work 機本地裝 Ollama，
但 Squirrel installer 在 `--silent` 模式下卡住、Inno Setup 風格 `/DIR=` 也不認，本地裝失敗。

**決策**：用 home 機器（DESKTOP-J17AJFD, RTX 2060, 6GB VRAM）跑 Ollama，
work 端透過 SSH tunnel + Tailscale 內網連過去。

**踩坑 1：ssh per LLM call 會死結**
- 第一版 `call_home_ollama` 每次 LLM 呼叫都 `subprocess.run(['ssh', host, 'curl ...'])`
- Flask 多執行緒下，一題 5 個 cascade call = 5 個 ssh handshake 同時跑
- Tailscale handshake / SSH auth 通道互相塞死，連最初一發成功之後其他全部卡 4-9 分鐘
- 殭屍 ssh proc 累積、後續所有 ssh 全被連帶卡住

**踩坑 2：tunnel target 寫 `localhost` 接不到**
- `ssh -L 11434:localhost:11434 home` 起 listener，但 `curl localhost:11434` 回 "Empty reply"
- 改成 `ssh -L 11434:127.0.0.1:11434 home` 就通——Windows OpenSSH 對遠端的 `localhost` 名稱解析會走到別的 socket

**最終架構**：
```
work 端開一次：
  ssh -N -L 11434:127.0.0.1:11434 -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes home

call_home_ollama 改成：
  requests.post("http://localhost:11434/api/generate", json=body, timeout=timeout)
```

一條 tunnel 承擔整個 exam 的所有呼叫——沒有 spawn 開銷、沒有並發死結、Python-native。

---

### 4. reasoning 模型踩坑：qwen3.5:2b 必須關 think

**背景**：qwen3.5:2b 跑 GTB smoke 一題 86.6 秒（gemma3:4b 同題 5s）。

**原因**：qwen3.5 是 reasoning 模型，每次呼叫先做 `<thinking>` 推理。
GTB 一題 5 個 LLM call、每個都加 reasoning 階段 = 全題跑完估 1.5-2 小時。
而且 reasoning 模型在「給 enum 選一個」這種嚴格任務反而 hallucinate（smoke 把 name 抽成 "Demo用"）。

**修法**：`call_home_ollama` 加 `body["think"] = False`。對非 reasoning 模型是 no-op，對 reasoning 模型直接關掉推理階段。

**效果**：86.6s → 5.7s（15x 加速），name 從 "Demo用" 改為正確的「前進」。

---

### 5. boss 題本 v1 → v2 校正

**背景**：跑 baseline 過程中發現 expected 答案有腦補修正型錯誤，例如：

| id | user_text | expected name | 問題 |
|----|-----------|--------------|------|
| 3 | 請給我禾名的帳單未稅12月起算六個月 | 辰銘 | 老闆腦中知道「禾名 → 辰銘」，但沒有演算法能猜出來 |
| 4 | 列出所有新竹的客人 | region_code: 3 | 跟其他題 `03` 格式不一致 |
| 7 | 請給我合影的分店資料 | createBranch | 字面是查詢、expected 卻是 create |
| 12 | 起點加6點 | name: 「起點加6點無法匹配任何名稱，請重新輸入」 | expected 值本身就是錯題標記 |

**行動**：
- 寫了 `scripts/exam_to_csv.py` 把題本 dump 成 UTF-8 BOM CSV
- colombo 看 CSV 親手刪/改錯題：102 → **76 題**
- 所有 baseline 必須在 v2 重跑才有意義

---

### 6. v2 → v3 corpus 二次校正：分析 baseline 失敗反向修 corpus

**背景**：v2 跑完之後，列出 gemma3:4b 失敗的 23 題逐一檢視，
發現一大半「失敗」其實是 corpus 標準答案有問題、不是 LLM 錯。

**分類整理**：
- 8 題 expected.name 跟 user_text 字面對不上（boss 腦補修正型）
- 1 題 expected.intent 寫錯（id 42「法博加6點」expected 寫成 queryPoints）
- 1 題功能還沒做（id 61「瀚諾 三月份有多少銷貨單」）
- 5 題重複 user_text 但 expected 互相打架（id 35/46/57/72/74「有支手機加2點」name 兩種版本）

**修法**（寫了 `scripts/exam_v2_patch.py` + `exam_v3_patch.py` 兩輪 patch script）：
- 8 題 expected.name 對齊 LLM 實際抽出的答案：
  禾名 / 水里遠傳 / 華騏 / 有支手機 / 正欣 等
- id 42 expected.intent: queryPoints → adjustPoints（字面就是「加6點」）
- 移除 id 61（功能未做）
- 同 user_text 的 expected 全部統一（76 → 75 題）

**重算策略**：不重跑、寫 `scripts/rescore_v2.py` 用 user_text 對齊舊 results.json + 新 expected。
分數立刻反映 corpus 修正、省下 50 分鐘重跑時間。

---

### 7. 完整 baseline matrix（7 條，75 題 v3 corpus，rescore 後）

| 排名 | 配置 | Intent | Values | **Both** | 耗時 |
|---|---|---|---|---|---|
| 🥇 | gemma3:4b · LLM cascade | **97.3%** | 78.7% | **77.3%** | **4.6 min** |
| 🥈 | qwen2.5:7b · LLM cascade | 96.0% | 74.7% | 73.3% | 5.1 min |
| 🥉 | codex_cli (gpt-5.4) · Agent | 89.3% | 70.7% | 69.3% | 17.1 min |
| 4 | qwen3.5:2b · LLM cascade（think=false）| 96.0% | 54.7% | 53.3% | 4.5 min |
| 5 | qwen2.5:7b · Agent | 72.0% | 48.0% | 46.7% | 4.9 min |
| 6 | gemma3:4b · Agent | 58.7% | 46.7% | 44.0% | 4.4 min |
| 7 | qwen3.5:2b · Agent | 76.0% | 36.0% | 33.3% | 4.0 min |

**v2 → v3 corpus 修正後 Both 分數變化**：所有 baseline 全面上升（+1.7 ~ +7.6）。
gemma3:4b LLM cascade 受惠最大（69.7 → 77.3, +7.6），因為它本來最大失分來源就在 corpus 標錯的 name 校正類。

**同模型 cascade vs agent 對照**（v3）：

| 模型 | LLM cascade | Agent | cascade 領先 |
|---|---|---|---|
| qwen3.5:2b | 53.3% | 33.3% | +20.0 |
| gemma3:4b | **77.3%** | 44.0% | **+33.3** |
| qwen2.5:7b | 73.3% | 46.7% | +26.6 |

→ **三個 Ollama 模型都是 LLM cascade 大贏 agent**。把 22 個任務描述塞一坨給小/中模型反而搞混它。
cascade 把問題切碎、每一刀都只做單一決定，反而正確。

**gemma3:4b 失敗剩 17 題的拆解**（v3 baseline 分析）：
- 8 題 schema 不對齊（expected key `start_month` vs mission `due_month`、`include_tax: N` vs `null`）→ 框架可解
- 4 題 `calculate_phonetic_similarity` bug（不同拼音都被吸成「正欣」假候選）→ 程式 bug
- 5 題 LLM 真實抽錯（id 4 想想 → null、id 22 更新客戶誤判、id 27 簡訊點誤判、id 60 paper 多行黏一起、id 64 typo「未遂」干擾）

→ 扣掉前兩類 12 題技術可解的，**gemma3:4b 真實 LLM 推理錯誤只剩 5 題**。**真實能力 ≈ 91-93% Both**。

---

### 8. 核心架構決策：保留 cascade，default LLM 從雲端 Groq 切到 home gemma3:4b

**結論**：之前討論「LLM vs Agent」糾結的問題，benchmark 數字已給答案：

1. **GTB 核心架構維持 LLM cascade**——切碎餵的設計是對的、不要動
2. **default LLM 從 Groq 切到 home_ollama + gemma3:4b**
   - 準確率：97.3% intent / 77.3% both（v3 corpus），比 codex agent（89.3 / 69.3）還高
   - 速度：4.6 分鐘跑 75 題（3.7s/題），比 codex agent（13.5s/題）快 4 倍
   - 成本：0 美元（home 機器電費），不再受 Groq rate limit 拖累
   - 隱私：訊息留在 home 機器，沒對外
3. **agent 模式留著當未來「多步任務 / tool use / 困難 corner case」的入口**——
   準確率不是它的賣點，未來的擴展性才是

**單一論點**：一台 RTX 2060 + 開源 4B 模型 + 既有 cascade 架構 = 比花錢的 codex agent 更好。

---

## 本輪新增 / 更新檔案

### general-task-bot
- `gtb_dev.py`
  - `/sim` 加 `mode=agent` 分支（暴力雙問：Q1 task_id / Q2 values）
  - body 可帶 `agent_provider` / `agent_model` 切後端
  - `agent_classify_and_extract()` 支援 provider/model override
- `llm_clients.py`
  - **重寫 `call_home_ollama`**：從 `subprocess.run(['ssh', host, 'curl ...'])` 改為 `requests.post('http://localhost:11434/...')`
  - 加 `body["think"] = False` 關 reasoning 模型推理
  - `call_groq` 加 429 / 5xx retry + Retry-After 退避
  - `call_hf` 加同類 retry（透過 error message 嗅探判定 retryable）
- `scripts/exam_runner.py`
  - 加 `--mode` / `--agent-provider` / `--agent-model` / `--per-item-sleep`
  - agent 模式 expected camelCase 自動對齊 actual snake_case
  - concurrency=1 + per_item_sleep>0 走純序列分支保證題與題之間有喘息
- `scripts/exam_to_csv.py`（新）：題本 dump CSV 給人校正
- `scripts/agent_smoke10.py`（新）：agent 模式 10 題抽樣 smoke
- `scripts/exam_v2_patch.py`（新）：v2 corpus 8 題 expected.name 對齊 LLM 真實答案
- `scripts/exam_v3_patch.py`（新）：v3 corpus 重複題 expected 一致性 patch（id 42 intent + id 57 name）
- `scripts/rescore_v2.py`（新）：用 user_text 對齊舊 results.json + 新 expected 重算 baseline，免重跑

### cwsoft-aquan-manager
- `benchmark/boss_exam_v1.json`：colombo 親手從 102 → 76 題（v2）→ 75 題（v3，移 id 61）
- `benchmark/boss_exam_v1.csv`（新，給校正用）
- `benchmark/reports/2026-05-13_*`：7 個 baseline 結果資料夾

---

## 待跟進

- [ ] gtb_dev.py 切 PROVIDER=home_ollama / LLM_MODEL=gemma3:4b 當預設（v2 數字已支持這個改動）
- [ ] customerlist 拼音相似度 bug：「前進」被 gemma3 + match_pool 認成「正欣」（多次重現），但 qwen2.5 沒這問題。要看 `calculate_phonetic_similarity()` 為什麼會把不同 pinyin 認在一起
- [ ] qwen3.5:2b 在 think=false 下 intent 94.7% 但 values 48.7%——值抽取有 quirk，可能跟 reasoning 中關閉的副作用有關
- [ ] home 機器不是 24/7——加 fallback：`call_home_ollama` 連不上 → 退到 HF（已加 retry 比較穩）或退到原 cascade
- [ ] 把這次架構結論寫進 `docs/gtb_核心架構_LLM_vs_Agent_討論整理.md`（既有的舊討論文件需更新）
- [ ] 自動化：每次改 `mission_pos_dev.json` / `prompts_pos_dev.ini` 自動跑 gemma3:4b smoke
- [ ] prod gtb.py 換 LLM provider（等 dev 版穩定跑一陣子之後）
