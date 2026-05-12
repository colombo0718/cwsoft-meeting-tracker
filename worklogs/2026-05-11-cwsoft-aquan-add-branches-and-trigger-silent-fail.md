# 阿全前進客戶新增三分店 × sqlgate trigger silent rollback bug 深挖

- 日期：2026-05-11
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-sqlgate、cwsoft-aquan-manager、general-task-bot

---

## 一、起點：客戶要 3 個新分店

「前進」客戶需新增三家分店：**三重龍門 / 中和景新 / 樹林立仁**。原本想當作「不同層次測試」逐層驗證：

```
Layer 1 = 直接 SQL 加（最底層）
Layer 2 = 走 sqlgate /add_branch API
Layer 3 = 阿全 LINE bot 自然語言
```

實際只走完 Layer 1，因為踩到 sqlgate add_branch 的根本性 bug，後兩層都通不了。

最終狀態（全部走 inline pyodbc 加成）：

| 編號 | 店名 | 狀態 |
|------|------|------|
| 3 | 三重龍門 | ✅ |
| 4 | 中和景新 | ✅ |
| 5 | 樹林立仁 | ✅ |

POSConfig.分店設定檔.店Code數 = 6，剛好對應 6 筆營業分店（含總倉）。

---

## 二、發現的核心 bug：sqlgate add_branch silent rollback

**現象**：透過 sqlgate POST `/add_branch?name=前進&shop_name=三重龍門` 回 `ok=true, affected=1`，但實際 DB **沒有那筆紀錄**。同時 POSConfig.店Code數 卻 +1 了（造成不一致）。

**鏈條**：
```
1. INSERT INTO [前進].dbo.分店 ...
2. 觸發 [前進].dbo.分店trig（AFTER INSERT/UPDATE/DELETE）
3. trigger 內 EXEC：
     dbo.加庫存給分店
     dbo.建立銷排銷量
     dbo.產生即時庫存（條件：聯盟客戶 join posconfig）
4. 某個 SP 內部 raise error → trigger 隱式 ROLLBACK
5. INSERT 被 rollback，但 pyodbc 沒收到 exception，rowcount 仍回 1
6. 後續 UPDATE POSConfig.分店設定檔 因為 transaction 已被 trigger 終止，
   變成 implicit auto-commit 進入 DB
7. 結果：分店表沒進、POSConfig +1 了、API 回成功
```

---

## 三、走過的歪路（紀錄錯誤推論的時序，避免下次重蹈覆轍）

### 推論 ❌ A：「linebot 帳號權限不足」

證據：sqlgate 用 linebot 連，加不進去。換 pos（sysadmin）inline 就成功。
反證：後來 sqlgate 改連 pos + autocommit=False 也仍失敗。**所以帳號不是根因**。

### 推論 ❌ B：「.env 的 Pos 跟 linebot 切換沒被讀到」

證據：sqlgate 是 nssm Windows Service，dotenv 在 import 時讀一次。
驗證：sqlgate 重啟後 PID 從 43976 → 396560，新 process 確實重讀 .env。
但是仍 silent fail。**.env 不是根因**。

### 推論 ⚠️ C：「pyodbc autocommit 模式問題」

部分對。實測：
- `pyodbc.connect(conn_str, autocommit=True)`（**connect 時設**）→ INSERT 仍 silent fail
- `conn = pyodbc.connect(conn_str); conn.autocommit = True`（**runtime 設**）→ INSERT 成功

兩者 `@@TRANCOUNT, @@OPTIONS` 都顯示 `(0, 5496)`，但實際行為不同。
這是 pyodbc / ODBC driver 的某種互動，原因未深究。**實證上「runtime 設」才有效**。

### 推論 ⚠️ D：「trigger 內 SP 對特定編號留下子表副作用」

部分證據支持：
- 編號 101 第一次 INSERT TEST_B 失敗（silent fail），之後再 INSERT 同編號（改名「中和景新」）也失敗
- 反例：編號 4 失敗多次後，inline INSERT 又能成功
- 編號 102 INSERT 顯示成功，但後續 UPDATE 永遠 silent fail（rowcount=1 但實際沒改），重試 3 次都同樣

這是個**機制不明的 trigger 行為**，跟具體子表狀態有關。`加庫存給分店` 等 SP 在不同編號上行為不一致。

### 結論

**sqlgate add_branch 的 silent fail，根因是 pyodbc autocommit 模式 + trigger 內 SP ROLLBACK 的綜合作用，外加部分編號的子表狀態污染**。三層交互讓 debug 過程繞了非常多彎。

---

## 四、過程中的累積爛攤

| 副作用 | 處理 |
|--------|------|
| POSConfig.店Code數 被 sqlgate 失敗 INSERT 多次 +1 | 手動 SQL 修回 4，後續成功 INSERT 自然 +1 對齊到 6 |
| 編號 100/102/103 三筆測試殘留（TEST_A/C/D） | 軟下架（是否已收店=1）— 100/103 成功，102 同樣 silent fail 留著 |
| sqlgate add_branch 被改了 `conn.autocommit = True` 但仍失敗 | 暫留改動但加註解「未完全修復」，待後續 SP 化 |

---

## 五、能繞過的方法

**真正可運作的加分店流程**：

```python
import pyodbc
conn = pyodbc.connect(conn_str)   # ← 不傳 autocommit 參數
conn.autocommit = True             # ← runtime 設（這個寫法才有效）
cur = conn.cursor()
cur.execute("""
    INSERT INTO [前進].dbo.分店 (..., 公司主索引, 建立日期)
    SELECT ?, ?, N'', N'', N'', 0, -1, 1, ..., ?, GETDATE();
""", (next_code, shop_name, company_index))
```

腳本：[cwsoft-sqlgate/scratch/add_branch_direct.py](https://github.com/colombo0718/cwsoft-sqlgate/blob/master/scratch/add_branch_direct.py)
（原本是 linebot 版本踩雷的，要用的話先改成 pos 帳號 + runtime autocommit）

---

## 六、對 sqlgate 修法的選項評估

| 方案 | 優點 | 缺點 |
|------|------|------|
| **A. sqlgate 全面改 connection runtime autocommit=True** | 改動小，繞過 silent fail | 失去 transaction 原子性，分店 INSERT 跟 POSConfig UPDATE 要分別 try/catch |
| **B. 寫 `[各資料庫設定].dbo.CreateBranch` SP，sqlgate 改 EXEC** | 仿 detach_customer 模式，繞過 pyodbc / trigger 互動 | 要 DBA（同事）寫 SP；命名要對齊現有慣例 |
| **C. 改 sqlgate add_branch 加 INSERT 後 immediate SELECT 自我驗證** | 至少 silent fail 變顯式 fail | 治標不治本 |
| **D. 把 sqlgate .env 永久改回 Pos** | 立刻可用 | sysadmin 給服務太大、安全風險 |

**建議優先序**：B（治本）> C（過渡監測）> A（可用但脆弱）> D（不建議）

順帶發現 sqlgate 還缺 `attach_customer` endpoint，但 SP `[各資料庫設定].dbo.AttachCustomer` 早就存在了——同類遺漏。

---

## 七、本日新增 / 改動文件

### cwsoft-sqlgate（待 commit）
- `app.py` add_branch 加 `conn.autocommit = True` runtime 設定 + 詳細註解（標明是 2026-05-11 加的，**未完全修復**只是繞過部分案例）
- `scratch/add_branch_direct.py` 新增（直接 SQL 加分店的可運作腳本）

### matrix-manager
- `meetings/2026-05-11-cwsoft-aquan-add-branches-and-trigger-silent-fail.md`（本檔）
- `INDEX.md` 同步更新

---

## 八、待跟進

### 立即（後續操作直接受影響）
- [ ] sqlgate add_branch 走 SP 化（建 `CreateBranch` + `CloseBranch` 兩個 SP，sqlgate 改 EXEC 呼叫）— 找同事討論
- [ ] sqlgate `attach_customer` endpoint 補上（SP 早就有）
- [ ] 編號 102 TEST_C 軟下架失敗的根本原因查清（是哪個子表的哪筆資料讓 trigger 內 SP 炸）

### 中期
- [ ] 補 `[各資料庫設定].dbo.CloseBranch` SP（規劃中的「下架分店」功能依賴它）
- [ ] sqlgate 各端點安全/穩定性掃過：autocommit、SQL injection、缺端點（5/7 接管會議已列）
- [ ] sqlgate 內呼叫從 cwsoft.leaflune.org 改 127.0.0.1（5/8 routing 遷移會議規劃）

### 長期
- [ ] sqlgate 改用獨立的 service 帳號（介於 linebot 跟 sysadmin 之間，只 grant 必要 SP 的 EXEC 權限）

---

## 附：當天的關鍵決策推導

### 「為什麼最後選 inline 加而不是修 sqlgate 上線」

debug 過程繞太久，user 最終決定先把客戶業務需求滿足（3 個分店加進去），sqlgate 修復另案處理。**業務優先於工程潔癖**——客戶不會因為 sqlgate 還沒修好就停止運作。

### 「為什麼 102 TEST_C 不繼續硬清」

100 跟 103 軟下架成功、102 失敗，重試 3 次都同樣。再 debug 對主目標沒幫助，且測試殘留不影響業務（前端只看營業分店）。**列為 known issue 比繼續鑽更務實**。

### 「為什麼會議記錄要詳細寫錯誤推論的時序」

debug 過程踩過 4 個錯誤推論才找到真因。如果只寫「結論：trigger silent rollback」，下次同類問題會再走一次冤枉路。**保留歪路是給未來省時間**。
