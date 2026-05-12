# cwsoft-liff-pages：門市圖片整理 × LINE 圖文選單換圖

- 日期：2026-04-27
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-sonnet-4-6)
- 相關專案：cwsoft-liff-pages

---

## 一、門市圖片整理

**背景**：LIFF 門市導覽網址改為 `?name=零壹通訊行`，root 的 store1~7.jpg 需要換成零壹通訊行版本。

**執行**：
- 新建 `宇新/` 資料夾，把原本 root 的 store1~7.jpg 存入備份
- 把 `零壹通訊行/store1~7.jpg` 複製回 root 取代
- Push to master → Vercel 自動部署

**目前圖片結構**：
```
cwsoft-liff-pages/
├── store1~7.jpg       ← 零壹通訊行版本（線上使用中）
├── 零壹通訊行/        ← 同一份備份
└── 宇新/              ← 宇新版本備份
```

---

## 二、LINE 圖文選單換圖（深色版）

**目標**：從現有淺色選單換成深色設計（Gemini 生成圖）。

**作業過程**：
1. 兩張設計稿存入專案，重新命名：
   - `rich_menu_1.png`（深色版，Gemini 生成）
   - `rich_menu_2.png`（淺色版，原設計）
2. LINE Channel Access Token 存入 `.env`，同步建立 `.gitignore` 避免 push 到 GitHub
3. 將 `rich_menu_1.png` 縮放至 800×540（LINE 最低規格）
4. 嘗試透過 LINE Messaging API 建立並設定預設圖文選單：
   - ✅ `POST /v2/bot/richmenu` 建立成功（richMenuId: `richmenu-22547782e7626891f84714c1e3779b6d`）
   - ✅ 圖片上傳成功
   - ❌ `POST /v2/bot/richmenu/default/{id}` 持續失敗

**API 失敗分析**：
- 初次嘗試被 Akamai CDN 擋下：HTTP 411 Length Required（未帶 `Content-Length: 0`）
- 修正後 LINE server 回傳 `{"message":"Not found"}`（原因未完全釐清，疑似帳號方案限制，另 `GET /v2/bot/followers/ids` 也回傳「Access to this API is not available for your account」）
- OA bot info：`chatMode: "chat"`，`全葳智慧門市 @990imlnk`

**結論**：設定預設圖文選單 API 在此帳號無法使用，最終由使用者至 LINE OA Manager 手動換圖完成。

---

## 三、LINE OA/LIFF API 能力盤點（本次釐清）

| 可 API 控制 | 不可 API 控制 |
|---|---|
| Rich Menu CRUD（建立/刪除/查詢） | OA 名稱、頭像、封面 |
| 圖片上傳 | OA Manager 手動建的 Rich Menu |
| 訊息發送（Push/Reply/Broadcast） | 回應模式切換（手動/Bot）|
| LIFF app 新增/更新/刪除 | 帳號方案相關限制功能 |

**注意**：OA Manager 建立的 Rich Menu 與 Messaging API 建立的是**完全獨立**的兩套系統，無法互相管理。

---

## 四、後續待確認

- [ ] 確認此帳號 LINE 方案層級，以及哪些 Messaging API 功能可用
- [ ] 若未來需要 API 自動換圖，需確認「設定預設圖文選單」API 是否可在更高方案啟用
