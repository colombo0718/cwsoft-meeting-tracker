# gtb_dev.py 後門開門 × 阿全測試版服務上線

- 日期：2026-05-12
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m]) × 另一個 Claude session（負責 aquan repo dev config 那條線）
- 相關專案：general-task-bot、cwsoft-aquan-manager、cwsoft-super-manager、cwsoft-ai-customer-service

> 承接 [2026-05-11-cs-shadow-empty-drafts-and-gtb-encoding-cleanup.md](2026-05-11-cs-shadow-empty-drafts-and-gtb-encoding-cleanup.md)
> 跟 [2026-05-12-aquan-tier-classifier-prep-for-backdoor.md](2026-05-12-aquan-tier-classifier-prep-for-backdoor.md)（對方 Claude 寫的 aquan 端準備）。
> 4/14 會議列為待跟進的「GTB 測試入口脫離 LINE OA」終於落地，並順手把阿全測試版（壓測用）的服務骨架架起來。

---

## 一、起點：要怎麼壓測 GTB

老闆希望阿全跑兩個版本：**正式版接 LINE 處理日常**、**測試版作大量壓測再上線**。要做到這件事，先卡在一個前置問題 — gtb_dev.py 目前唯一入口是 `/callback/<oaid>` LINE webhook，沒辦法用程式自動灌量。

4/14 會議 §9 已列為待跟進：在 gtb_dev.py 加 `--cli` / `--exam` 模式脫離 LINE。但拖到 5/12 才動。

---

## 二、後門設計拍板

跟 user 對齊三個關鍵設計選擇：

| 選擇 | 結果 |
|---|---|
| 後門對 LINE API 的行為 | **純 dry-run**（不打 LINE 也不模擬延遲）|
| dev config 跟 prod 設定檔分流 | **分一份** `mission_pos_dev.json` + `prompts_pos_dev.ini` |
| DB 怎麼處理 | **獨立 `database_dev/` 目錄** |

過程中 user 提醒了一個關鍵原則 — 「後門兩邊互動都是假的」：
- 向上對 LINE OA：不驗 signature、不打 LINE API
- **向下對 downstream API 也要假**：不真打 sqlgate / autoQuotes，只記錄會打哪支 API
- 後門目的：測 chatbot 跟人訊息互動的應答對不對 — 問對問題、組對 API 動作，**不測 SQL / 報價單副作用**

我第一版 `/sim` route 還真的 call `execute_command` 戳下游 → 違反原則 → 拿掉，只保留 `cmd_url` 當紀錄。

---

## 三、實作（gtb_dev.py 後門）

### 3.1 DB 路徑分流

- argparse 加 `--db-dir`（default `database`，向後相容 cs-shadow）
- `DB_PATH` / `CONFIG_DB_PATH` / `SHADOW_DB_PATH` 全改用 `DB_DIR = PROJECT_DIR/<args.db_dir>`
- `db_helper.get_or_create_conv_db` 簽名從 `project_dir` 改成 `db_dir`（body 不再寫死 `database/` 子目錄）— 只有一個 call site，安全改動

### 3.2 POST /sim/<oaid> route

跳 signature 驗證、不打 LINE、不真 call downstream。回 JSON 含：
- `intent` / `intent_chain` / `task_id`
- `values` / `missing` / `field_confidence`
- `cmd_url`（會打哪支 API 的紀錄）
- `timing_ms` / `errors`

---

## 四、配合對方準備的 4 層階梯式 classify_tree

對方（另一個 Claude session）同時在 aquan repo 做了一件大事 — 把 `mission_pos_dev.json` 從化石狀態（4/27 之後沒動）重做成 **4 層階梯式 classify_tree**：

```
tier1（5 最常用 + next）
  ├ adjustPoints / generateQuote / queryPoints / queryCredentials / generatePerip
  └ next → tier2 (5 + next)
            ├ addBranch / closeBranch / detachCustomer / setIntransit / RegionCustomers
            └ next → tier3 → tier4 → fallback_greeting
```

加上 4 個 tier extractor 的 prompt（嚴格 enum + regex format + 正反例）。設計理由：tier1 預期解 78% 訊息 → 平均一個訊息只跑 1.x 次 LLM call，token / latency 大降。

**但這擋住了 gtb_dev.py** — 現有 classify_tree 解析是單層的，遇到 `subtree` 就不會遞迴。

### 4.1 subtree 遞迴實作

抽出 `resolve_task_from_tree(tree, user_text, intent_chain)` helper，遞迴下去：
- 找 `branch.match == intent` → matched_branch
- 「null」/「next」都當 fallback 關鍵字（兼容平面 + 階梯）
- chosen branch 有 `subtree` → 遞迴；有 `task_id` → leaf 返回

**user 中途提醒**：「gtb 正式版先不要動阿」— 我一開始把 helper 也加進 gtb.py 跟改了 shadow mode call site，馬上 revert。最後只動 gtb_dev.py 的 3 個 call site（shadow / normal / sim）。

對 backward-compat：平面 mission_cs.json / mission_pos.json 在 gtb_dev.py 仍能正確跑（match="null" 路徑跟舊行為等價）。

---

## 五、Smoke Test 結果

aquan-manager-dev (port 6010) 起來後跑三組 case：

| Case | 預期 | 實際 | 判定 |
|---|---|---|---|
| 「幫零壹加100點」 | tier1 hit adjustPoints | `intent_chain=["adjustPoints"]`、task_id=`adjust_points` | ✓ 分類對 |
| 「幫前進新增一家分店三重龍門」 | tier2 hit addBranch | `intent_chain=["next","addBranch"]`、task_id=`create_branch` | ✓ 遞迴對 |
| 「hello, 今天天氣很好」 | 全 fallback | `intent_chain=["next","next","next","next"]`、task_id=`fallback_greeting` | ✓ 四層遞迴對 |

階梯遞迴本身**完全正確運作**。

---

## 六、順手發現的次要 bug：match_pool 拼音排序

`/sim` 對「幫零壹加100點」的回應，task_id 對、cmd_url 組出來、但 `values.name` 是「星威」（離譜，應該是「零壹通訊行」）。

抓出根因：`SequenceMatcher.ratio() = 2*M/(len1+len2)`，分母含 candidate 全長 → **短 keyword 對長 candidate 即使是完整前綴，分數仍被長度稀釋**：

```
keyword 「零壹」(lingyi, 6 字元):
  對「零壹通訊行」(lingyitongxunxing, 17): ratio = 12/23 = 0.52  ← #8
  對「星威」(xingwei, 7):                ratio = 8/13  = 0.62  ← #1
```

「零壹通訊行」只排第 8 名。

**這 bug 不是後門引入的** — gtb.py / gtb_dev.py 都共用同一套演算法（各有一份 copy）。

### 為什麼 prod 沒撞到

gtb.py `gather_fields` 開頭有個 **substring preprocess 救濟**（hardcoded）：訊息含 candidate 全字串 → 直接覆寫，跳過拼音比對。老闆實務說全名「零壹通訊行」 → substring hit → 不走拼音比對 → 撞不到。

但 `gtb_dev.py` `gather_fields` **沒這層救濟**，加上我用短版「零壹」做 test case → 暴露 bug。

### 處理方式

user 決定**寫進 gtb TODO.md，交給另一個 Claude 處理** — 這 bug 不是後門驗收項目，後門本身已通過。詳細修法選項見 `general-task-bot/TODO.md` 新加的 `[BUG] match_pool 拼音比對：短 keyword 對長 candidate 排序錯` 條目。

---

## 七、附帶完成

### 7.1 cs-shadow 影子模式加圖片支援

承接 5/11 cs-shadow 修復後，user 反映「圖片沒進來」— shadow_messages 表 user_message 欄存 `[圖片]` 字串、admin UI 顯示不出實際圖片。

按 `docs/shadow_mode_三個_bug_修正計畫.md` §「後續：圖片顯示完整方案」實作：
- `gtb.py` `init_user_message_table` 加 `image_path TEXT` 欄位 + ALTER TABLE migration
- `gtb.py` shadow 區段：msg_type=image 時立刻打 LINE Content API 下載到 `database/images/<message_id>.jpg`（Content API 短時間內有效，事後拉不到）
- `gtb.py` `save_shadow_message` 簽名加 `image_path` 參數
- `admin_server.py` 加 `GET /admin/image/<filename>` route + `get_messages` SELECT 加 image_path
- `admin/app.js` `renderCard` 偵測 `image_path` → 渲染 `<img>` 標籤

### 7.2 影子模式介面忍者 emoji

user 順手要求：admin 介面分頁標籤 + 上方標題欄加忍者 🥷。第一版只塞 emoji 到 `<title>` 文字 → user 用內聯 SVG favicon 範例糾正 → 改用 `data:image/svg+xml,<svg ... 🥷</text></svg>` 作為 favicon，topbar 文字保留 emoji。

### 7.3 services.json 加 aquan-manager-dev

```json
{
  "name": "aquan-manager-dev (6010)",
  "cmd": ["py", "-3", ".../gtb_dev.py", "--conf", "pos_dev", "--port", "6010", "--db-dir", "database_dev"],
  "cwd": ".../cwsoft-aquan-manager",
  "port": 6010,
  ...
}
```

`nssm restart cwsoft-super-manager` → 服務 spawn 成功、PID 157712、status=running。

---

## 八、本日成果

### 已 commit（未 push，等下次 RDP）

- `general-task-bot`：
  - gtb_dev.py 加 `/sim` 後門 + `--db-dir` arg + subtree 遞迴
  - gtb.py 加圖片下載（shadow 模式）
  - db_helper.py 簽名調整
  - TODO.md 加 `[BUG] match_pool 拼音排序` 條目
  - docs/gtb_後門動工清單.md（5/12 上半段寫的）
  - docs/gtb_正式版_開發版_盤點.md（5/12 上半段寫的）
- `cwsoft-ai-customer-service`：
  - admin_server.py + admin/app.js + admin/index.html 圖片支援 + 忍者 emoji
- `cwsoft-super-manager`：
  - services.json 加 aquan-manager-dev
- `cwsoft-aquan-manager`（對方做）：
  - mission_pos_dev.json 重做成 4 層階梯
  - prompts_pos_dev.ini 加 4 個 tier extractor
  - docs/gtb_後門配合_aquan端準備.md

### 還未動工

- `scripts/exam_runner.py` 並發考題 runner
- boss_chat.txt → 題本（102 筆抽樣）標 expected_intent / expected_task_id
- 跑第一輪壓測 + 出準確率報告

---

## 九、與其他 Claude 的協作邊界

### 對方做的
- aquan repo `config/` 兩個 dev 檔重做（4 層階梯式）
- 寫了 `docs/gtb_後門配合_aquan端準備.md` 對齊雙邊狀態

### 本 session 做的
- gtb_dev.py / db_helper.py 後門實作 + subtree 遞迴
- super-manager services.json 加 aquan-manager-dev
- cs-shadow 圖片功能 + 忍者 emoji
- TODO.md 加 match_pool bug

### 交界紀錄
- 對方文件指出阻擋點是 gtb_dev.py 不支援 subtree 遞迴 → 本 session 解除
- 對方建議的 `resolve_task_from_tree` 演算法做了小修改：「null」/「next」都當 fallback 關鍵字，並把信心值機制整合進去（雖然 dev mission 沒開）

---

## 十、待跟進

### 立即
- [ ] commit + push 三個 repo（aquan repo 還沒 git init，這條等對方）
- [ ] aquan repo `.gitignore` 預留 `database_dev/`（等 git init 時加）

### 短期（接著做）
- [ ] `scripts/exam_runner.py` 並發 runner
- [ ] boss_chat.txt → 題本，需人工 + gemini 半自動標 expected
- [ ] 跑第一輪測試，看階梯式 vs 平面準確率對照

### 由另一個 Claude 處理
- [ ] `[BUG] match_pool 拼音比對：短 keyword 對長 candidate 排序錯`（user 5/12 交付）

### 中期
- [ ] 階梯式準確率 > 平面後，把階梯結構回寫 prod `mission_pos.json` + gtb.py 加 subtree 遞迴
- [ ] 6/1 零壹進階行銷上線前的兩項配套：LIFF 前端遷 office、阿全 mission_pos.json 內部呼叫改 127.0.0.1

---

## 附：當天關鍵決策推導

### 「為什麼 subtree 遞迴只加 gtb_dev.py，不加 gtb.py」

user 中途叫停（「gtb 正式版先不要動阿」）。prod 阿全是真實接 LINE 處理老闆業務，演算法改動風險高。階梯式 mission 也只有 dev 在用（prod mission_pos.json 還是平面），改 gtb.py 沒有立即價值。**等階梯式驗證可用後再回寫 prod**。

### 「為什麼向下對 API 也是假的」

user 一開始我直覺實作「會打 sqlgate」，被糾正：壓測 / 考題會大量觸發下游，每個 GET 都消耗 sqlgate connection + SQL Server 資源。即使是 read-only query 也不該成為壓測副作用源頭。考題重點是「組對 cmd_url」，sqlgate 自己的 SP 正確性那是 sqlgate 的測試範疇。

### 「為什麼 cs-shadow 切回正式版 gtb.py」

5/12 上半段做的事 — cs-shadow 之前跑 gtb_dev.py 是「占位」（沒人主動安排，是 cs-shadow 設定那時 gtb_dev.py 已經夠用）。盤點後發現 cs 完全不需要 dev 版獨有功能（mission_cs.json 沒設 with_confidence、沒 match_pool、shadow 模式不走 db_helper），切回 gtb.py 等於把 dev 版 free 出來讓本 session 改也不會炸到 cs-shadow。

### 「為什麼後門 vs 阿全測試版是兩件相關但獨立的事」

- 後門 = gtb_dev.py 加 `/sim` route（程式碼層）
- 阿全測試版 = services.json 加新 service entry + aquan repo 加 dev config（部署層）

兩件事分開做利於 debug：
- 後門壞 → 任何 gtb_dev.py 服務（包括 cs-shadow）都會跟著掛
- 阿全測試版設定錯 → 只影響 6010 port 那條，不影響 cs-shadow

第一次 smoke test 用 cs config（簡單平面）驗證「平面結構仍 work」，再切到 pos_dev（4 層階梯）驗證遞迴 — 一步步排除變數。
