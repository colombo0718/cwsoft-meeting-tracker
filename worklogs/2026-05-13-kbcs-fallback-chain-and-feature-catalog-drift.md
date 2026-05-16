# cs-shadow 草稿 incident × kbcs fallback chain × feature_catalog 設計撞牆

- 日期：2026-05-13（整天，從 db_introspect 上線到 sqlgate 新 endpoint 設計撞牆）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-ai-customer-service、general-task-bot、cwsoft-sqlgate、cwsoft-super-manager

> 承接 [2026-05-12-cwsoft-governance-cleanup-and-overview-doc.md](2026-05-12-cwsoft-governance-cleanup-and-overview-doc.md)。
> 5/12 把 cwsoft 治理跟 OVERVIEW.md 收尾後，5/13 整天分兩條線：
> （A）緊急修 cs-shadow 客戶面草稿吐錯字串問題；
> （B）sqlgate 兩個新 endpoint（feature_catalog / feature_toggle）動工到撞牆。
> 中間還補了 db_introspect 工具上線跟一些 schema 探索。

---

## 一、tools/db_introspect.py + AGENTS-vbnet-pos.md 上線

user 早上把 gtb repo 裡錯置的 `AGENTS.md`（內容是 VB.NET + MSSQL 工作 SOP）跟 `tools/`（db_introspect.py + line_fetch_messages.py）**搬進 super-manager**。

搬遷時做了三件 secret 衛生：
1. `AGENTS.md` 改名 `AGENTS-vbnet-pos.md`（檔名直接點出範圍，不會被誤當 super-manager 自身的 agent 規範）
2. `line_fetch_messages.py` **拔掉 hardcoded LINE token**（搬進 super-manager = 上 GitHub，原檔 11 行寫死 token）→ 改成讀 env var
3. `.env.example` 建立（MSSQL_* + LINE_CHANNEL_ACCESS_TOKEN 範本）+ `.gitignore` 加 `.env` / `tools/.env`

實際 `.env` 從 gtb/tools/.env 拷貝（user 同意），跑 `db_introspect ping` 確認連線到 `cwsoft.com.tw,1226 / WIN-I97EH4BHSDO / 帳號 pos`。

---

## 二、用 db_introspect 驗證 boss wishlist 5 個 toggle 在 DB 真實狀況

對照 boss_chat.txt 提的 5 件「客戶功能切換」wishlist（#30/#46/#55/#63/#76），用 db_introspect 跑 `SELECT 名稱, 設定值 FROM dbo.基本設定 WHERE 名稱 LIKE ...`：

| user 講的（自然語）| DB 實際欄位 | 當前值（POSV3測試專用）| 結論 |
|---|---|---|---|
| 維修站系統 | `維修站` | 1 | ✅ 找到（名稱漂移：「系統」沒在 DB）|
| 總倉銷售 / 總倉銷貨 | `總倉可銷貨` | 1 | ✅ 找到（DB 用「可銷貨」更精確）|
| 自訂成本 | `自訂成本` | 1 | ✅ exact match |
| **手機版** | **❌ 沒有 toggle** | — | 最接近的是 `行動裝置數量=5`（quota 數值，不是 0/1）|

`search 手機版` 全 schema-wide 只找到 2 個 VIEW（毛利報表）— 確認**「手機版」不是 boolean toggle**。「法博移除手機版」實際操作多半是把 `行動裝置數量` 改 0，是 quota 行為不是 toggle。

→ 對應 sqlgate 新 endpoint 設計：5 件 wishlist 中 **4 件能用通用 toggle endpoint 解，1 件（手機版）要當資源管理另議**。

---

## 三、cs-shadow incident：admin 看到「LLM 呼叫失敗：429」

下午 user 報：cs-shadow admin 介面客戶訊息很多 ai_draft 是錯誤字串，不是正常草稿。

### Trace 路徑

```
LINE 客戶訊息
  ↓
[Layer 1] cs-shadow (gtb.py port 6003, shadow 模式)
          ├─ run_extractor 意圖分類 → call_provider("groq", ...)
          │  ✓ 有 fallback：Groq 429 → 自動轉 hf  (這層 work)
          └─ task_id = query_knowledge_base
             → execute_command GET http://127.0.0.1:6004/answer?sections=...
   ↓
[Layer 2] kbcs (kbcs_server.py port 6004)
          └─ inline call_groq() 整合 KB + 生草稿
             ✗ 沒 fallback：Groq 429 → except → return "（LLM 呼叫失敗：429...）"
                字串
   ↓
cs-shadow 把這字串當「KB 回答」存進 shadow_messages.ai_draft
```

關鍵理解：**gtb.py 跟 kbcs 是兩個獨立服務、各自呼叫 Groq，fallback 邏輯不共享**。gtb.py 第一層救得了它自己的意圖分類，救不了 kbcs 的 KB 草稿生成。

### 修法（連著踩兩個雷）

第一輪修法：把 kbcs 的 inline call_groq 改走 `llm_clients.call_provider`，配三層 fallback chain `groq → hf → home_ollama`。原以為這樣就好。

**但實測 prod 後 ai_draft 變成空字串（比錯誤字串還慘）**。trace 到兩個爆雷同時：

1. **HuggingFace Inference API 改付費了**（2026 起）— Llama-3.3-70B-Instruct 不在免費 tier，呼叫回 **402 Payment Required**。原本當「免費備援」的 hf 直接掛掉。
2. **home_ollama 太慢** — colombo 自家 RTX 2060 + ssh tunnel + 70B model cold start ~20 秒，**超過 gtb.py `execute_command` 的 10 秒 timeout** → gtb 端視為失敗 → ai_draft = ""

第二輪修法：
- **拿掉 hf**（402 沒救）
- **拿掉 home_ollama**（cold start 太慢，cold-start 解決前不能上 prod chain）
- **加 openrouter** 當 groq 備援（付費但 2.69s 穩定回 200）

最終 chain：

```python
LLM_FALLBACK_CHAIN = [
    ("groq",       "llama-3.3-70b-versatile"),            # 主：免費 + 快（~0.5s）
    ("openrouter", "meta-llama/llama-3.3-70b-instruct"),  # 備援：付費但穩（~2.7s）
]
```

### 連帶改了 llm_clients

`call_groq` / `call_hf` 內部各自有 5 次 exponential retry，撞 Retry-After header 可能等到 60s。對 single-provider 場景合理，但**對 kbcs 這種有外層 fallback chain 的場景就是傷害** — 第一個 provider 一直 retry，鏈條切不過去。

→ `call_groq` / `call_hf` 加 `max_retries` 參數（預設 4 保留向後相容），kbcs 用 `max_retries=0` 跑 **fail-fast** 立刻切下一層。

`call_provider` 也補上 `**kwargs` pass through。

### 結果驗證

連 5 輪 /answer 測：
```
round 4: HTTP 200 4.79s    (warm-up)
round 5: HTTP 200 3.27s
round 6: HTTP 200 2.67s
round 7: HTTP 200 1.95s
round 8: HTTP 200 2.83s
```

log 顯示 `[kbcs] groq failed: http 429` 後接 200 — fail-fast + fallback 路徑跑通。

---

## 四、insight：HF 改付費 + home_ollama cold-start = 雲端 LLM 策略要重排

過去設定（2025 末）是：「groq 主、hf 備援、home_ollama 兜底」— 三層都 free。

現實 2026-05：
- **groq**：免費 tier 限額硬（30 req/min / 14400 req/day），常撞 429
- **hf**：Llama-3.3-70B-Instruct 改 paid only（**新發現**）
- **home_ollama**：自家 RTX 2060 + ssh tunnel + 70B 大模型 cold start ~20s，**對 LINE webhook 等 user-facing 服務不可用**

→ 結論：**雲端 LLM「全免費」時代結束**，至少要付 openrouter / Groq Pro / 自己跑 GPU 主機才能保穩定。

→ home_ollama 不是死局，但**需要 keep-alive 預熱機制**（Ollama 預設 keep_alive=5min，連續使用時 hot < 1s）— 未來建一個 cron 每 4 分鐘 ping 一次 home gemma3:4b 就能保 hot，那時可以回鍋進 fallback chain。

---

## 五、sqlgate /feature_catalog + /feature_toggle 動工到撞牆

5/13 較早討論過：sqlgate 不要逐 wishlist 加 endpoint，做兩個通用 pattern endpoint：
- `/feature_catalog` — 中央功能目錄查詢
- `/feature_toggle` — 通用客戶功能切換

實作完 read-only 的 catalog 直接用 db_introspect 驗證 SQL，再加進 sqlgate/app.py。restart sqlgate prod，curl 測 `/feature_catalog?keyword=維修` → **count=0**。

### 撞到的牆：catalog 跟現實 drift 嚴重

中央 `各資料庫設定.dbo.開關` table（我設計時當 catalog）：
- **沒有** `維修站` / `總倉可銷貨` / `自訂成本` / `行動裝置數量` 這 4 條
- 有的是 `維修單廠商收費` / `維修檢查imei` / `總倉編號` 等別的、跟 boss wishlist 對不起來
- 大量 row 標 `唯讀=true` 但實際上 UI 是會改的 — flag 不可信

→ 我原設計「`/feature_toggle` 要求 feature 必存在 catalog 且唯讀=0」會**把 boss wishlist 全部擋掉**。

### user 一句話拆穿 over-engineering

user 問：「要調整的東西不是就都在基本設定 這個資料表裡嗎？」

對。事實 grounded 之後：
- `[客戶DB].dbo.基本設定` 是 EAV table，**boss 想 toggle 的東西全在這**
- 中央 `各資料庫設定.dbo.開關` **跟現實嚴重 drift**，不能當 ACL 權威源
- 用 drift 的 catalog 當 gate 是把自己的腳綁起來

### 簡化設計（5/13 結束時的方向，還沒實作）

```
/feature_catalog?name=<客戶DB名>
  → 列出 [客戶DB].dbo.基本設定 全部 row（這個客戶真實有的設定）
  → optional ?keyword=維修 過濾

/feature_toggle?name=&feature=&value=
  → UPDATE [客戶DB].dbo.基本設定 SET 設定值=? WHERE 名稱=?
  → ACL 簡化為：row 必須已存在（不允許新增 ad-hoc row）
  → 中央 開關 唯讀 flag 拿掉檢查
```

user 5/13 結尾選擇暫停這條，明天再決定 (1)/(2)/(3) 哪個方向繼續。

### 5/13 結束時 sqlgate 的狀態

- `/feature_catalog` 已加（read-only，目前查 `開關` table — drift，要重做）
- `/feature_toggle` 已加（含 UPDATE 能力，但 **整天從未被 invoke 過**，audit log 確認）
- sqlgate prod 跑著新代碼，但 toggle 端點實質上是 dormant 狀態（要 caller 主動打才會觸發）

---

## 六、本日成果

### cwsoft-super-manager
- 新檔：`AGENTS-vbnet-pos.md`（從 gtb 搬，改名）
- 新檔：`tools/db_introspect.py` + `tools/line_fetch_messages.py`（從 gtb 搬）
- 新檔：`.env.example`、`.env`（後者 gitignored）
- `.gitignore` 加 `.env` / `tools/.env`

### general-task-bot
- `llm_clients.py`：`call_groq` / `call_hf` 加 `max_retries` 參數；`call_provider` 接 `**kwargs` pass through

### cwsoft-ai-customer-service
- `kbcs_server.py`：inline call_groq 改走 `llm_clients.call_provider` + fallback chain（groq → openrouter）
- 重啟 prod 服務

### cwsoft-sqlgate
- `app.py`：新增 `/feature_catalog` + `/feature_toggle` endpoint（catalog drift 問題未解，下次重做）
- 重啟 prod 服務

### Claude 認知更新
- HuggingFace Inference 2026 起 Llama-3.3-70B 改付費（過去的「免費備援」假設失效）
- 中央 `各資料庫設定.dbo.開關` 跟現實 drift，**不能當 ACL gate**
- gtb.py `execute_command` 預設 timeout=10s 是設計上限，下游服務（kbcs）回應必須在這範圍內

---

## 七、待跟進

### 立即
- [ ] 把 sqlgate /feature_catalog + /feature_toggle 改成「grounded in 客戶DB 基本設定」的版本（5/14 動工）
- [ ] 暫時保留 toggle endpoint dormant（沒被叫過、不會誤觸）

### 短期
- [ ] commit + push 三個 repo 的改動（super-manager / general-task-bot / cwsoft-ai-customer-service / cwsoft-sqlgate）
- [ ] cs-shadow 流量再觀察 1-2 天，確認 fallback chain 在 prod 穩定
- [ ] kbcs 的 admin 介面文字回覆功能完整測試（傳圖功能 user 決定先不做，需要走 LINE OA Manager 自己後台）

### 中期
- [ ] home_ollama keep-alive 預熱機制（cron 每 4 分鐘 ping 一次）→ 可以放回 fallback chain
- [ ] 中央 `各資料庫設定.dbo.開關` 的 `備註` 欄位漸進填 alias map（老闆口語 → DB 欄位），靠人工維護
- [ ] 補 boss_exam_v1.json 漏掉的 13 個 intent（addCustomer / addDevice / closeBranch 等）

### 長期
- [ ] sqlgate 全 17 個既有 endpoint 的 SQL injection audit（PROJECT.md 提到的 `[name]` f-string 風險）
- [ ] DR plan 等羿宏 5/16 回國後重啟（plan 已寫但 9 個問題沒答完）

---

## 附：當天的關鍵推導

### 「為什麼 catalog 跟現實 drift 是設計取捨而非 bug」

`各資料庫設定.dbo.開關` 是「中央定義文件」性質，加新 row 要動中央 schema；
但客戶 DB 的 `dbo.基本設定` 是 EAV 自由結構，新功能可以直接寫進去不用先過中央。

工程現實 → 永遠是「動手實作的」先進客戶 DB、「補中央文件的」拖一拖。
→ catalog 嚴重落後是制度問題，不是 schema bug。

教訓：**設計 ACL 不要 grounded 在「會落後的中央 catalog」上，要 grounded 在「能跟現實對齊的 source」上**（這裡就是客戶 DB 自己的 基本設定 row 已存在 = 該 row 是合法 toggle target）。

### 「為什麼 fail-fast 設計比 retry 設計適合 fallback chain」

call_groq 內建 retry：對 single-provider 場景合理（撐過 burst）。
但 kbcs 有外層 fallback chain：撞 429 時，繼續 retry groq vs 立刻切 hf — 後者顯然快。
→ retry 跟 fallback chain 是兩種互斥策略，**疊起來只會讓總等候時間爆炸**。
→ 加 `max_retries` 參數讓兩種 caller 各自選自己要的策略。

### 「為什麼 HuggingFace 改付費對整個 cwsoft AI 策略影響大」

過去設計（cwsoft-vision.md / h2-direction.md）一直把 HF 當「永久免費備援」— 因為 HF 過去有寬鬆免費 tier 跑開源模型。

2026 起政策改後，**70B 級模型 free tier 收掉**。這意味著：
- 客服自動化 10% / 50-80% 的 KPI 不能再假設 LLM 零成本
- 需要評估付費方案（openrouter pay-as-you-go / Groq Pro / 自架 GPU）
- 或調整模型策略（70B → 7B-13B 仍能跑 free，但品質下降）

這該回流到 cwsoft-vision.md 跟 cwsoft-h2-2026-direction.md 的「LLM 成本」段落更新。
