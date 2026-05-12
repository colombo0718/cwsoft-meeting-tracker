# cwsoft 星威 hotfix × 首次跑完完整發版流程

- 日期：2026-05-11
- 參與者：colombo0718 × Claude (claude-haiku-4-5)
- 相關專案：cwsoft-pos / AI 客服知識庫

> 同事 kobe 出國中，colombo 第一次獨立處理「找 bug → 修程式 → commit → build → 打包 update25.exe → 上傳 FTP」整條 release 鏈。順便把 SVN / MSBuild / 批次處理發版工具的肌肉記憶建立起來。

---

## 案例：星威 5/8 異常

### 客戶症狀
1. 基本設定 → 專案商品設定 → 跳 `DataBinding 無法從清單中找到適用於所有業結（繫結）的資料列`（CurrencyManager.FindGoodRow 失敗）
2. 銷售畫面 → 加入新會員 → 跳 `接近關鍵字 'and' 之處的語法不正確`

老闆在他電腦也能複製。

### 診斷踩的坑

| 階段 | 想法 | 結果 |
|------|------|------|
| 一開始 | 老闆推測：客戶端 Windows 時間格式 | 老闆自己也跳，排除 |
| 第二輪 | 我推測：代碼表（專案內容/種類）空 | 鑫譽也空但不跳，排除 |
| 第三輪 | 我推測：`基設_專案設定2.vb` 第 592/603/615/626 行 4 個 binding 綁到 DB 不存在欄位（違約金、合約等）| **誤判**。雖然程式碼確實這樣寫，但客戶點的是「專案商品設定」（沒帶 2），不是「專案商品設定2」。這條線是另一個 bug 但不是這次的根因 |
| 第四輪 | colombo 自己跑卻不跳，差異是「working copy 沒 update」→ 轉用 SVN 對比 r372 vs r373 | **解開** |

### 真正的根因

**Bug 1：r373 在「基設_專案設定.vb」加了 chk是否算點 binding，但 ds專案設定2 DataSet 漏定義「是否算點」column**

- 第 2068 行新增：`Me.chk是否算點.DataBindings.Add(...,"專案.是否算點"...)`
- 但 `ds專案設定2.Designer.vb` 只加了「點數」column，**漏了「是否算點」**
- CurrencyManager 推資料時找不到 DataSet column → FindGoodRow 失敗 → 跳錯
- DB 端的「是否算點」欄位實際上存在（bit NULL），不是 DB 問題，是 DataSet 漏定義

**Bug 2：r373 在「基設_會員資料輸入.vb」加了 UCload會員群組()，新增會員時觸發但 edit會員編號 為空**

```vb
where c.會員編號=  and  o.過時 = 0
```
缺值直接接 `and` → SQL 語法錯誤。

觸發路徑：銷售畫面 加入新會員 → ShowDialog → Form_Load → b加入新會員=True → btnAdd_Click → btn回復_Click → UCload會員群組() → 拼壞的 SQL。

### Hotfix

| 檔案 | 修法 |
|------|------|
| `設定/基設_專案設定.vb` 第 2068 行 | 註解 chk是否算點 的 DataBindings.Add |
| `設定/基設_會員資料輸入.vb` 第 2887 行 | UCload會員群組 加 `IsNullOrWhiteSpace` 檢查，空值直接 return |

兩個都「讓行為退回 r372 之前的樣子」，不引入新邏輯。

---

## 首次跑完完整發版流程

之前 colombo 平常只負責「客戶問答」，發版這條鏈都是 kobe 在做。這次 kobe 出國，整條流程第一次自己跑完：

1. **SVN 操作**：`svn update` / `svn cleanup` / `svn revert -R .` / `svn update -r 372` / `svn log -v -r 373` / `svn diff -c 373` / `svn commit`
2. **MSBuild Release**：用命令列 `MSBuild "手機進銷存v2.sln" -p:Configuration=Release`（注意：要先關掉 VS 偵錯 + POS exe，不然 dll 被鎖）
3. **打包 update25.exe**：
   - 從 FTP 下載當前的 update25.exe（這是 SFX 格式的 archive）
   - 用 WinRAR `a -m5 -ep` 把新檔案加進去（覆蓋同名舊檔案）
   - 上傳回 FTP
4. **批次處理 GUI**：「上傳更新檔」綠色按鈕做的就是上面這套流程。後續跳出來的 UPDATE SQL（更新主畫面公告跑馬燈）是**獨立**的，hotfix 救火可以跳過

---

## 心得

### 1. 找 bug 要善用 SVN diff，不要靠目測程式碼推
這次最大彎路：我看到 `基設_專案設定2.vb` 第 592 行有 binding 綁到 DB 不存在的「違約金」欄位，就推測那是根因。但實際上：
- 這個 bug 從 r372 之前就存在，不是 r373 引入的
- 客戶實際點的是另一支 form（沒帶 2 的舊版）
- 真正的根因在 `基設_專案設定.vb`（沒帶 2）+ `ds專案設定2.Designer.vb` 漏 column

教訓：當 colombo 跟客戶/老闆出現「行為不一致」時（colombo 不跳、其他人跳），第一直覺就應該是 **SVN diff**，而不是繼續猜程式碼。

### 2. 用 VS 例外狀況設定攔 SqlException 是 SQL 拼接 bug 的捷徑
對於「接近關鍵字 'and' 之處的語法不正確」這類 SQL Server 端訊息，最有效的不是看程式碼猜，是：
- 偵錯 → Windows → 例外狀況設定 → 勾 `System.Data.SqlClient.SqlException`
- F5 重現
- VS 會停在 ExecuteSQL / Fill 那行
- 即時運算視窗 `?sql` 看實際送出的 SQL 字串
- 一秒看出「`where c.會員編號=  and`」缺值

### 3. r373 是個「未完成的重構」
kobe 一次 commit 25 個檔案，包含主畫面、專案設定、會員資料輸入、前台銷售、即時庫存、進階行銷平台等大幅改動。但「基設_專案設定.vb 加了 chk是否算點 binding」卻**漏了補 `ds專案設定2.Designer.vb` 的對應 column**，這是典型的「重構做到一半就 ship」狀況。

未來提醒：大幅改動分段 commit、發版前在測試 DB 跑全流程。

### 4. 「不知道精確根因前不要動」是好原則，但要設停損點
我繞了三個錯誤方向之後才轉用 SVN diff。如果一開始就接受「我不知道，先看歷史」，會省下不少時間。下次「猜超過兩輪都不對」就該換策略，不要繼續鑽。

### 5. 「治標 vs 治本」要看脈絡
中間有一輪我建議「把 4 行 DataBinding 註解掉」當解法，colombo 質疑「這不是治本」。當下我重新看了一遍才發現方向錯了。
教訓：使用者的「直覺懷疑」常常有道理，不要為了堅持自己的判斷而硬辯，先重新檢查再說。

---

## 待跟進

- [ ] kobe 回國後通知他兩個 hotfix 的位置（已寫在 `c:\Users\USER\Desktop\POS3\星威_5月8日異常_診斷與修復報告.md`）
- [ ] kobe 補完「是否算點」整套功能：`ds專案設定2` 加 column、`基設_專案設定.vb` 把 binding 還原並加 NullValue=False
- [ ] 觀察 5-10 分鐘內有沒有客戶反映新 bug；若有要從 SVN 退回 r374、重 build、重新上傳
- [ ] 整理「客服診斷 SOP」加上「colombo/客戶行為不一致時先 SVN diff」這條
