# sqlgate add_branch SP 化重構 × LINE→DB 端對端打通

- 日期：2026-05-11（傍晚，承接同日上午會議）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-sqlgate、cwsoft-aquan-manager、general-task-bot

> 承接 [2026-05-11-cwsoft-aquan-add-branches-and-trigger-silent-fail.md](2026-05-11-cwsoft-aquan-add-branches-and-trigger-silent-fail.md)。
> 上半天確認 sqlgate add_branch 因 trigger silent rollback 不可靠，先用 inline pyodbc 把 3 家分店加給「前進」客戶。
> 下半天動手做根本解：把寫入邏輯包成 SP，sqlgate 改 EXEC，並驗證從 LINE 端能完整跑通。

---

## 一、為什麼決定走 SP 路線

下半天再回頭測 sqlgate add_branch，發現問題比上午盤點還多：

| 變數 | 結果 |
|------|------|
| linebot 帳號 + autocommit=False | silent fail |
| pos 帳號 + autocommit=False | **仍然 silent fail** |
| pos 帳號 + connect-time `autocommit=True` | silent fail |
| pos 帳號 + runtime `conn.autocommit = True` | **inline 直接跑可成功，但 sqlgate POST 仍 silent fail** |
| 完整模擬 sqlgate 流程（同樣 pos + runtime autocommit），但**用 inline python script 不走 Flask** | **成功** |

唯一變數差是 **Flask werkzeug HTTP 處理層**。具體機制（multi-thread / Flask exception 吞噬 / werkzeug 跟 ODBC 互動）沒查明，但**結論很清楚：在 Flask 環境裡靠 pyodbc 直接寫 + trigger 互動 = 不可靠**。

SP 化的優勢：**整段 SQL 在 SQL Server 端執行**，Flask 端只負責送 `EXEC` 跟接 result，繞開 pyodbc/trigger/Flask 三層互動的詭異區。

---

## 二、建立的兩個 SP

放在 `[各資料庫設定].dbo` schema，跟現有 `DetachCustomer` / `CreateCustomer` / `AttachCustomer` 等對齊命名與位置。

### `[各資料庫設定].dbo.CreateBranch(@db_name, @shop_name)`

職責：
1. 驗證客戶存在於 POSConfig
2. 動態 SQL 算 `MAX(分店編號)+1`
3. 檢查店名重複
4. `BEGIN TRAN` → INSERT 分店 + UPDATE POSConfig.店Code數 → COMMIT
5. 全程 `BEGIN TRY / BEGIN CATCH` 包，trigger 內 ROLLBACK 會被 CATCH 抓到回 FAIL（不再 silent）
6. 回傳 result set：`status / branch_code / err_msg`

### `[各資料庫設定].dbo.CloseBranch(@db_name, @branch_code)`

職責：
1. 驗證分店存在 + 未下架
2. `BEGIN TRAN` → DELETE 庫存（對齊歷史 SOP）→ UPDATE 分店.是否已收店=1 → UPDATE POSConfig.店Code數-1 → COMMIT
3. 同樣 TRY/CATCH
4. 回傳 result set：`status / shop_name / err_msg`

部署腳本：[cwsoft-sqlgate/scratch/install_branch_sps.py](https://github.com/colombo0718/cwsoft-sqlgate/blob/master/scratch/install_branch_sps.py)（建檔 + 之後改了就 redeploy）

### 走過的小彎路

- 第一版 SP 加了「INSERT 後 SELECT 自己」當 verify → 結果踩 **transaction isolation 看不到自己** 的雷，誤判 FAIL。
- 改解法：把 verify 移到 SP **外部**（sqlgate 端用另開 connection 查回）。SP 本身只負責執行，verify 是呼叫端的責任。

---

## 三、sqlgate 改 endpoint

`app.py` 動了三個地方：

1. **新 helper `_sp_connection()`**：runtime `conn.autocommit = True`（避免 Flask + autocommit=False 的 silent fail）
2. **`/add_branch` → `/create_branch`**（snake_case 對齊其他 endpoint、動詞跟 SP 對齊）
   - 全部改用 `EXEC [各資料庫設定].dbo.CreateBranch ?, ?`
   - SP 回 OK 後**用獨立 connection 外部 verify** 才回 ok=True
   - 從 150 行縮到 50 行
3. **新增 `/close_branch`**（呼叫 CloseBranch SP，同樣有外部 verify）

阿全的 `mission_pos.json` 對齊更新：
- task_id `add_branch` → `create_branch`
- url_template 改 `/sqlgate/create_branch`
- classify_tree `addBranch → create_branch`（保留意圖名稱不變）
- `close_branch` task **暫未接 LINE**（identify_needs 還沒加 closeBranch 意圖、mission 沒加 task 定義；sqlgate 端 endpoint 已 ready）

---

## 四、LINE→DB E2E 過程踩的雷（依序）

從第一次 LINE 測試到通，連續修了 5 個獨立問題：

| # | 現象 | 根因 | 修法 |
|---|------|------|------|
| 1 | 訊息「POSV3測試專用 開新分店 店名 龍安店」抽取 `name=龍安店, shop_name=龍安店` | `identify_name` prompt 的 regex 限制 `{2,7}` 字，但「POSV3測試專用」是 9 字 → LLM 為了守 regex 放棄 hardcode 「最高優先 POSV3測試專用」rule | regex 上限 7 → 10 |
| 2 | LLM 重跑同樣訊息又抽錯 | LLM 隨機性（Llama temperature 0.3 仍有變異） | gtb.py 加 hardcode preprocess：訊息含 customerlist 客戶名 → 直接強制覆寫 name 欄位，跳過 LLM |
| 3 | 確認時回「對」卻被當成取消 | `extracted_ronot` prompt 列舉的肯定詞沒包含「對」 | 補「對 / 好的 / 沒錯 / yep / 就這樣」等口語肯定詞 |
| 4 | LINE webhook 跑兩次（cancel 舊指令 + 跑新任務） | gtb.py 邏輯：`extracted_ronot=null + human_check=true` 取消舊但**沒 return**，繼續跑主流程 | 設計上其實是對的（新指令不該被當作舊指令的回應），保留行為，但要記得清舊 pending |
| 5 | sqlgate POST 雖透過 SP 成功但 verify 抓不到 | 之前 inline 測試留下 sleeping pyodbc connection sid=165 hold transaction，造成 SELECT 拿不到 commit 後的資料 | KILL hung sessions，後續用「每個 SP call 都獨立 connection + 立即 close」 |

最後成功的 LINE 互動：

```
[使用者] POSV3測試專用 開新分店 店名 龍安店
[阿全] 任務判定：create_branch
       抽取欄位：{'name': 'POSV3測試專用', 'shop_name': '龍安店'}
       最終指令：/sqlgate/create_branch?name=POSV3測試專用&shop_name=龍安店
       執行模式：先詢問確認
       預覽：將在「POSV3測試專用」新增分店「龍安店」，預計編號 19

[使用者] 好

[阿全] 待辦處理：確認執行
       執行結果：POSV3測試專用 已新增分店「龍安店」（編號 19）
```

---

## 五、清掉的測試殘留（admin 操作）

過程中累積測試殘留：
- [前進] 編號 100/102/103（TEST_A/C/D）
- [POSV3測試專用] 編號 19/20/21（龍安店2/4/5）

直接 `DELETE FROM 分店` 會踩 trigger silent rollback。摸索出標準流程：

```sql
-- 1. 清 FK 子表（庫存等）
DELETE FROM [<DB>].dbo.庫存 WHERE 分店編號 IN (...);
-- 2. DISABLE 分店trig（避免 trigger 內 SP 失敗）
DISABLE TRIGGER [分店trig] ON [<DB>].dbo.分店;
-- 3. 真 DELETE
DELETE FROM [<DB>].dbo.分店 WHERE 分店編號 IN (...);
-- 4. ENABLE 還原
ENABLE TRIGGER [分店trig] ON [<DB>].dbo.分店;
```

完整 SOP 寫進 [cwsoft-sqlgate/docs/分店硬刪除SOP.md](https://github.com/colombo0718/cwsoft-sqlgate/blob/master/docs/%E5%88%86%E5%BA%97%E7%A1%AC%E5%88%AA%E9%99%A4SOP.md)，**不對外開 endpoint**（admin only）。

---

## 六、本日新增 / 改動文件

### cwsoft-sqlgate（待 commit）
- `app.py`：`/create_branch` + `/close_branch` 都走 SP + 外部 verify、新增 `_sp_connection()` helper
- `.env`：DB_USERNAME 改 `Pos`（linebot 註解掉）— 雖然根本解是 SP 化，但 Pos 帳號保留以避免未來新功能再踩
- `docs/分店硬刪除SOP.md`：新增 admin 級分店硬刪除標準流程
- `scratch/install_branch_sps.py`：CreateBranch / CloseBranch SP 部署腳本
- `scratch/add_branch_direct.py`：純 inline 加分店腳本（早上留下，現在純參考）
- `scratch/_new_branch_endpoints.py`：sqlgate code 重構時的中介檔

### cwsoft-aquan-manager
- `config/mission_pos.json`：`add_branch` task → `create_branch`、url_template 對應改 `/sqlgate/create_branch`、classify_tree 同步
- `config/prompts_pos.ini`：`identify_name` regex `{2,7}` → `{2,10}`、文字描述對齊

### general-task-bot
- `prompts_system.ini`：`extracted_ronot` 規則 1 補「對 / 好的 / 沒錯 / yep / 就這樣」、規則 2 補「不、不要、不行、算了、不對」
- `gtb.py`：`gather_fields` 加 hardcode preprocess（訊息含 pool 內客戶名 → 強制覆寫，跳過 LLM 不穩）

### SQL Server
- `[各資料庫設定].dbo.CreateBranch` 新增
- `[各資料庫設定].dbo.CloseBranch` 新增

### matrix-manager
- `meetings/2026-05-11-sqlgate-branch-sp-refactor-and-line-e2e.md`（本檔）
- `INDEX.md` 同步更新

---

## 七、待跟進

### 立即
- [ ] cwsoft-sqlgate / cwsoft-aquan-manager / general-task-bot 三個 repo 的本日改動 commit + push（aquan-manager 仍待上 git）
- [ ] 把編號 102 TEST_C 那筆 silent rollback 故事的後續結案說明（[前進] 那邊已經 hard delete 清掉）

### 短期
- [ ] **LINE bot 加上「下架分店」功能**（sqlgate `/close_branch` endpoint 已 ready）：
  - `prompts_pos.ini` 的 `identify_needs` 加 `closeBranch` 意圖（觸發詞：「下架分店」「關店」「停用 X 店」）
  - `mission_pos.json` 補 `close_branch` task 定義 + classify_tree 對應 + `get_branch_code` 欄位
- [ ] sqlgate 順手補 `attach_customer` endpoint（SP `AttachCustomer` 早就有，sqlgate 沒接，5/7 會議遺留）
- [ ] gtb.py / accountSystemServer.py 補真 `/health` endpoint（取代當前的 lucky pass）

### 中期
- [ ] sqlgate 各 endpoint 都檢視「是否走直接 SQL 寫入」（add_customer / add_device / adjust_points 等），若是的話評估是否需 SP 化避免類似 silent fail
- [ ] sqlgate 的 cmd 加 `-u` flag（services.json `["py", "-3", "-u", "app.py"]`）讓 print 即時 flush，今天 debug 時 print 訊息被 buffer 隱藏的問題不要再發生
- [ ] gtb.py 是否該寫對話歷史到 DB（目前正式版只有 print → super-manager log，沒像 gtb_dev.py 的 message_log 表）

### 長期
- [ ] 把 sqlgate 「直接 INSERT/UPDATE 觸發 trigger」這類模式都改成 SP 化，避免 pyodbc/Flask/trigger 三層互動的不可預期
- [ ] 評估 sqlgate 是否該獨立 service 帳號（介於 linebot 受限 跟 Pos sysadmin 之間，給最小 SP exec 權限）

---

## 附：當天的關鍵決策推導

### 「為什麼最後選 hardcode preprocess 而不是再優化 prompt」

當天試過 prompt 改 regex / 加最高優先 rule / 加範例三輪，同樣訊息有時抽對有時抽錯——這代表問題不在 prompt 文字，是 **LLM 本質上對 prompt rule 的遵守不穩定**。再優化 prompt 是邊際收益。

程式層 preprocess（訊息含 customerlist 完整客戶名 → 強制覆寫）是 deterministic，繞過 LLM 隨機性。對「客戶名稱已知且完整在訊息裡」這種情境，根本不該交給 LLM 判斷，這是該硬寫 code 的場合。

### 「為什麼 verify 從 SP 內挪到 sqlgate 端」

SP 內 BEGIN TRAN/COMMIT context 下 SELECT 自己 INSERT 的 row，會因為 transaction isolation 看不到（讀的是 commit 前的 snapshot）。如果硬要 NOLOCK 又會看到 dirty data。**正確架構是：SP 負責執行、呼叫端負責驗證**。各層責任清楚比較不會掉雷。

### 「為什麼一個 LINE 訊息可以同時 cancel 舊指令 + 跑新任務」

gtb.py 設計上：使用者送業務訊息時，**不該被當作對舊指令的回應吞掉**。舊指令該被優雅地視為 abandoned，新訊息照走主流程。這個行為其實是對的，今天看了一下原本以為 bug 結果是 feature。

### 「為什麼 sqlgate POST 一直靜默失敗、但 inline 同樣 SQL 就 work」

下半天追到剩**唯一變數 = Flask werkzeug HTTP 層**。具體機制沒查清（可能 multi-thread / Flask exception 吞噬 / werkzeug 對 stdout buffering），但這個謎已經不重要——SP 化把整段邏輯搬到 SQL Server 端執行就繞過了。**未必每個謎都要解清楚，繞過比追根究底更務實**。
