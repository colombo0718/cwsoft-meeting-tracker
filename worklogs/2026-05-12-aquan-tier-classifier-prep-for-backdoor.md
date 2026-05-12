# aquan 端配合 gtb_dev 後門：階梯式分類器準備

- 日期：2026-05-12
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m]) × 另一個 Claude session（gtb_dev 後門那條線）
- 相關專案：cwsoft-aquan-manager、general-task-bot

> 本檔聚焦 **aquan repo 這條線**。對方 Claude 同時在做 gtb_dev.py `/sim` 後門 + super-manager dev 服務 + 考題 runner，主清單在 [general-task-bot/docs/gtb_後門動工清單.md](https://github.com/colombo0718/general-task-bot/blob/master/docs/gtb_%E5%BE%8C%E9%96%80%E5%8B%95%E5%B7%A5%E6%B8%85%E5%96%AE.md)。

---

## 一、起點：兩個 _dev 檔是 4/27 化石

阿全的 `cwsoft-aquan-manager/config/` 有兩組設定：

| 後綴 | 檔案 | 狀態 |
|------|------|------|
| `pos`（正式）| `mission_pos.json` + `prompts_pos.ini` | 阿全 LINE 跑這組（services.json 設 `gtb.py --conf pos`）|
| `pos_dev`（開發）| `mission_pos_dev.json` + `prompts_pos_dev.ini` | 4/27 之後沒人動，化石 |

對方 Claude 在 gtb_dev.py 開了 `/sim` 後門 route（不打 LINE、不打 downstream，只記 cmd_url），但需要 aquan 端把 `pos_dev` 復活才能跑。

---

## 二、為什麼選方案 B（復活 pos_dev）

討論過三種路線：

| 方案 | 優點 | 缺點 | 採用 |
|------|------|------|------|
| A. 直接動 prod 加階梯 | 最快 | 阿全 LINE 直接受影響，cwsoft-aquan-manager **還沒上 git**，沒退路 | ❌ |
| B. 復活 pos_dev 當試驗場 | 安全隔離、可比 prod/dev 對照 | 要起新 service、可能要新 LINE OA | ✅ |
| C. 直接動 prod，先 git init | 一勞永逸補 git debt | 範圍過大，要先做 git 再做主任務 | 暫緩 |

採 B 配 **C 的 git debt 還是要還**（在 aquan TODO 已列）。

---

## 三、核心設計：4 層階梯式分類器

### 3.1 為什麼從樹狀走階梯

之前討論過樹狀（hierarchy）vs 階梯（cascade）：
- **樹狀**：按邏輯類別分（讀/寫/結構/維護）。問題是「哪個 task 屬哪類」是工程師主觀決定，業務變化時要重編
- **階梯**：純按使用頻率分梯。資料驅動，自我優化，每層 prompt 短而具體

階梯的關鍵洞察：「**人不會被訓化成知道自己屬於什麼分類樹**」。從訊息**句構/用詞**反推分類，比按邏輯屬性分類更貼近 LLM 的能力邊界。

### 3.2 從 boss_chat.txt 撈頻率分梯

`cwsoft-aquan-manager/boss_chat.txt` 6 個月真實對話 102 筆：

```
adjust_points       43 筆 (42.2%)  ← 一家獨大
generate_quote      15 筆 (14.7%)
query_points        10 筆 ( 9.8%)
fallback_greeting    8 筆 ( 7.8%)  ← 不算正經 task
query_credentials    7 筆 ( 6.9%)
generate_perip       5 筆 ( 4.9%)
add_branch           4 筆 ( 3.9%)
detach_customer      3 筆 ( 2.9%)
set_intransit        3 筆 ( 2.9%)
region_customers     2 筆 ( 2.0%)
refresh_companies    1 筆 ( 1.0%)
adjust_sms_points    1 筆 ( 1.0%)
```

**22 個 task 裡只有 12 個有真實使用紀錄**，其他 10 個（query_sms_points / company_name / get_intransit / restore_test_db / rebuild_inventory / add_device / close_branch / add_customer / export_off_shelf / extend_due_date）6 個月內完全沒被用過。close_branch / extend_due_date 是今天剛加的新功能，沒歷史資料但老闆會用。

### 3.3 4 個梯隊配置

| 梯隊 | 內容 | 累積覆蓋 |
|------|------|---------|
| Tier 1 | adjustPoints / generateQuote / queryPoints / queryCredentials / generatePerip | **78.5%** |
| Tier 2 | addBranch / closeBranch / detachCustomer / setIntransit / RegionCustomers | + 分店/客戶生命週期 |
| Tier 3 | extendDueDate / refreshCompanies / adjustSmsPoints / addCustomer / restoreTestDB | + 少數但重要 + 高風險 |
| Tier 4 | querySmsPoints / companyName / getIntransit / rebuildInventory / addDevice / exportOffShelf | + 罕用 6 個 |
| (final) | next → fallback_greeting | catch-all |

每層 prompt 輸出 `matched intent` 或 `next`（交下一梯）。最深層 next 直接 → fallback。

### 3.4 預期效益

- **78.5% 訊息一次 LLM call 解決**（Tier 1 直接命中）
- 各 tier prompt 從「22 選 1」變「6 選 1（含 next）」，LLM 心智負擔大幅降低
- 相鄰但易混淆的 task 可以刻意分到不同 tier（例：今天 extendDueDate 跟 refreshCompanies 在 prod 平面架構下被誤判，階梯下分別在 Tier 3/3 跟 Tier 1/2 之外）

---

## 四、實際改動

### 4.1 baseline 同步（先確保 dev = prod）

之前 4/27 化石跟 prod 已差很多（缺 create_branch / close_branch / extend_due_date 等今天加的）。

```
cp mission_pos.json → mission_pos_dev.json
cp prompts_pos.ini  → prompts_pos_dev.ini
```

### 4.2 mission_pos_dev.json 改階梯式

- `version: 3 → 4` 標示新格式
- 新增 `_comment_classify_tree` 註解說明
- `classify_tree` 從平面 22 選 1 改成 4 層遞迴樹
- 每個 branch 可以是 leaf（`task_id`）或內部節點（`subtree`）
- task 區段（22 個 task 定義）**完全不動**

### 4.3 prompts_pos_dev.ini 加 4 個 extractor

- `identify_tier1` 6 輸出
- `identify_tier2` 6 輸出
- `identify_tier3` 6 輸出
- `identify_tier4` 7 輸出
- 每個 tier 結構統一：嚴格 enum + regex + 觸發詞 + 5+ 正面範例 + 1～2 個「該交下一梯」反例
- 原本的 `identify_needs`（平面 22 選 1）**保留作對照組**

### 4.4 prod 兩個檔完全沒動

`mission_pos.json` 跟 `prompts_pos.ini` 在這階段是 **唯讀**（cp 來源），沒寫回去。阿全 LINE 行為不受影響。

---

## 五、設計決策（回答對方 Claude 提問）

對方文件「五、與其他 Claude 的協作邊界」列了 3 個問題，我這邊的決定：

### Q1：dev config 要不要開 `with_confidence: true`？
**A：不開。** 第一輪純測「階梯式 vs 平面」分類正確率，先排除 confidence 機制當變數。等階梯式驗證可用後，再決定要不要疊上 confidence。

### Q2：dev config 對 `match_pool` 怎處理？
**A：共用 prod 的 `customerlist.txt`。** 避免 dev/prod 客戶清單不一致造成「分類對但欄位錯」這種偽陽性結果。142 個真實客戶名沒有「測試專用」隔離概念。

### Q3：`database_dev/` 進 `.gitignore`？
**A：等 aquan repo 上 git 才能做。** 5/7 super-manager 接管會議列為待辦至今未做。這個是阻擋項。

---

## 六、阻擋點：等對方做什麼

### 🚨 關鍵：gtb_dev.py 的 classify_tree 解析要支援遞迴

樹狀結構需要 gtb_dev.py 在跑 classify 時：
- 看到 branch 有 `subtree` 欄位 → 遞迴下去再跑一次 LLM
- 看到 branch 有 `task_id` → leaf 直接決定 task

從 prod gtb.py 看現有邏輯是**單層**的（`for branch in classify_tree["branch"]` 沒處理 `subtree`）。建議改 ~10 行就能支援遞迴，且**對 prod 安全**——因為 prod mission 還是平面結構（無 `subtree`），遞迴邏輯遇到平面退化等價於舊行為。

對方做完後就能跑階梯式測試。

### 其他配合事項
- 對方 services.json 加 `aquan-manager-dev (port 6010)` entry
- 對方寫考題 runner（`scripts/exam_runner.py`）
- 我這邊準備題本：從 boss_chat.txt 抽 102 筆 + 標 expected_intent / expected_task_id

---

## 七、本日新增 / 改動文件

### cwsoft-aquan-manager
- `config/mission_pos_dev.json` — cp 自 prod 後改 4 層 classify_tree（version 4）
- `config/prompts_pos_dev.ini` — cp 自 prod 後加 4 個 tier extractor
- `docs/gtb_後門配合_aquan端準備.md` — **新建**，給對方 Claude 參考的協作說明

### general-task-bot
- `docs/gtb_後門動工清單.md` — 對方寫的，本檔不動

### matrix-manager
- `meetings/2026-05-12-aquan-tier-classifier-prep-for-backdoor.md`（本檔）
- `INDEX.md` 同步更新

---

## 八、待跟進

### 立即（等對方）
- [ ] 對方加 `subtree` 遞迴解析到 gtb_dev.py
- [ ] 對方 `/sim` 後門 smoke test
- [ ] 對方 services.json 加 aquan-manager-dev (6010)
- [ ] 對方寫 exam_runner.py

### 我這邊
- [ ] 從 boss_chat.txt 抽 102 筆 → 標 expected_intent / expected_task_id → 存 `cwsoft-aquan-manager/benchmark/boss_exam_v1.json`
- [ ] 第一輪測完看 fail case，迭代各 tier prompt
- [ ] 階梯式準確率驗證 OK 後，回寫到 `mission_pos.json`（prod）+ `prompts_pos.ini`（prod）

### 衛生補完
- [ ] cwsoft-aquan-manager 上 GitHub private（5/7 待辦至今未做，這個一直拖）
- [ ] 上 git 後 `database_dev/` 加 `.gitignore`

---

## 附：當天的關鍵決策推導

### 「為什麼樹狀分類後又改階梯式」
原本想按邏輯類別（讀/寫/結構/維護）分樹，但意識到：**人講話不會按工程師的分類心智模型講**。樹狀分類本身會變成另一個「需要設計+維護」的系統。

階梯式直接按頻率分，**完全不用想哪些是同類**。資料驅動、易擴展、頻率變了重排就好。

### 「為什麼第一輪不開 with_confidence」
階梯式本身就是一種「降低 LLM 判斷負擔」的設計。第一輪要量測的是「階梯式架構本身有沒有效」，confidence 機制疊上去會讓變數變多、難歸因。確定階梯式有效後，再加 confidence + clarification 是下一階段。

### 「為什麼放棄方案 A」
直接改 prod 配 git revert 是常見 escape hatch，但 cwsoft-aquan-manager 連 git 都還沒 init。這個 debt 5/7 接管會議就列了，到現在沒做。在沒 git 的狀態下動 prod = 真的沒退路。改用 dev 是務實選擇。

### 「為什麼不直接編對方文件」
原本想在對方的 `gtb_後門動工清單.md` 加「對方端進度更新」段，但被 user 提醒拿掉。理由：**雙 Claude 協作時，各寫各的文件、互相 cross-reference 比較乾淨**。對方的主清單由對方維護，我這邊的進度由我寫在自己的 `gtb_後門配合_aquan端準備.md`。
