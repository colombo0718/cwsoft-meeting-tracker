# cwsoft POS 巡檢截圖腳本實作

- 日期：2026-03-24
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-sonnet-4-6)
- 相關專案：POS3、cwsoft-ai-customer-service

---

## 討論摘要

### 1. 背景與目標

先前已請 Claude 讀取 POS3 原始碼並整理出文字版《系統操作說明》（`POS3/系統操作說明.md`）。  
本次目標是補充**截圖素材**，讓 AI 客服有視覺參考，方法是寫一支腳本自動巡覽全部選單功能並截圖存檔。

**決策**：以 Python + win32gui 對安裝好的 POS（`C:\Program Files (x86)\全葳資訊\速利通訊專業進銷存\`）進行截圖，而非在 POS3 開發環境執行。

---

### 2. 失敗原因分析（前次嘗試）

前次腳本能截圖，但無法控制 POS 進入各子介面。原因：

| 問題 | 說明 |
|------|------|
| POS 是 32-bit，Python 是 64-bit | pywinauto 需注入目標 process，bitness 不符導致 AccessDenied |
| POS 以系統管理員身份執行（高完整性） | Python 以一般使用者執行（中完整性），UIPI 阻擋所有 SendInput / PostMessage / SendMessage |

**決策**：腳本必須以**系統管理員身份執行**，才能跨越 UIPI 限制。

---

### 3. 選單結構與技術方案

透過 win32gui 讀取主視窗的 `MainMenu` handle，以 ctypes 枚舉所有 MenuItem（含文字與 ID）。  
POS 用的是 WinForms 舊式 `System.Windows.Forms.MainMenu`（非 MenuStrip）。

- 全系統共找到 **183 個葉節點功能項目**
- 選單 ID 從 257 開始依序編號
- 透過 `PostMessage(hwnd, WM_COMMAND, menu_id, 0)` 直接觸發每個功能

**決策**：不用鍵盤模擬，改用 WM_COMMAND by ID，更穩定。

---

### 4. 登入對話框自動處理

許多功能開啟後會先彈出員工登入框（`frm_登入畫面`），需自動填入帳密。

分析來源（`POS3/使用者/使用者_登入畫面.vb`）：
- `txt_編號`（上方）：員工編號，Enter → 跳密碼欄
- `txt_密碼`（下方）：密碼，Enter → 呼叫 `check_valid()`

**登入框偵測邏輯**：視窗寬度 < 500px 且剛好有 **2 個 EDIT 子控制項**  
**自動填入**：用 `WM_SETTEXT` 直接寫入兩個 TextBox，再對密碼欄送 Enter

帳號：`1001`，密碼：`12345`

---

### 5. 跳過的項目

以下項目腳本自動略過，避免破壞系統狀態：

- `離開`、`版本切換`（正常版 / 測試版 / 舊資料庫）
- `分店切換`（各分店名稱）
- `登入/轉換`
- `銷售人員1～5`
- `手動更新資料`、`資料重整`
- 名稱為 `MenuItem`（無中文名稱的中繼選單）

---

### 6. 腳本輸出

截圖存放至：
```
C:\Program Files (x86)\全葳資訊\速利通訊專業進銷存\巡檢截圖\YYYYMMDD_HHMMSS\
```

命名規則：`{序號:03d}_{選單路徑}.png`，如：
```
000_主畫面.png
001_前台銷售_銷售.png
002_前台銷售_繳費.png
...
```

---

## 本輪新增 / 更新文件

| 檔案 | 說明 |
|------|------|
| `C:\Program Files (x86)\全葳資訊\速利通訊專業進銷存\巡檢截圖.py` | 巡檢截圖腳本（172 行 → 最終 372 行，含自動登入） |

---

## 待跟進

- [ ] 以管理員 cmd 執行 `巡檢截圖.py`，確認 183 項功能是否都能正常截到
- [ ] 確認登入框自動填入是否穩定（WM_SETTEXT 路徑）
- [ ] 若有功能開啟時跳出 MessageBox 確認框，需另外處理關閉邏輯
- [ ] 截圖完成後，決定如何整合進 AI 客服知識庫（與 `2026-04-16-cwsoft-pos-knowledge-card-schema.md` 的知識卡架構對齊）
