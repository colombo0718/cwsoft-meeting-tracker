# cwsoft 基礎建設統整 × super-manager 建置 × 跨專案文件標準化

- 日期：2026-04-27
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-sonnet-4-6)
- 相關專案：autoQuotes、cwsoft-super-manager、cwsoft-aquan-manager、cwsoft-ai-customer-service、cwsoft-sqlgate、cwsoft-clerk、cwsoft-liff-pages、cwsoft-product-scout、cwsoft-meeting-tracker、general-task-bot

---

## 討論摘要

### 1. autoQuotes — 進階行銷系統報價單（一次性）

**背景：** 零壹通訊行即將導入公司行銷系統，需要獨立產出一份不走一般 POS 月租費流程的報價單。

**決策：** 建立獨立腳本 `generate_marketing_quote_零壹.py` 處理這筆報價，不修改主流程。

計費規則：
- 豐原總店：3,000/月，其他 4 間分店：1,000/月 × 各 12 個月
- 合計：84,000 元（未稅），期間 2026/05/01–2027/04/30
- 使用現有 `quote_template2.html` + pdfkit 產出 PDF

外網存取路徑：`https://cwsoft.leaflune.org/output_quotes/` 透過 Cloudflare tunnel → Caddy → Flask 靜態路由提供。

---

### 2. CWSoft 服務架構全面梳理

**背景：** 公司有 11 個常駐服務，過去靠一個個 VSCode terminal 手動啟動監控，容易遺漏、難以重啟。

**釐清的架構事實：**
- GTB 是引擎，aquan-manager / cs-shadow / xiaohao 各自從自己的專案目錄呼叫 `gtb_dev.py`
- cwsoft-liff-pages 為 Vercel 靜態部署，不需本機服務
- cs-shadow 用 `--mode shadow` 啟動（AI 客服影子模式）
- cloudflared → Caddy (port 7000) 為聯外入口，Caddyfile 主控在 `C:\Program Files\cloudflared\`
- 完整 Caddyfile 在 `C:\Program Files\cloudflared\Caddyfile`（cwsoft-sqlgate/ 下的是舊版）
- port 6001 `/pos/*` 路由目前疑似未使用（留待確認）
- store GTB (port 6002) 目前停用；該 OA 改承接 LIFF 頁面

**服務清單（11 個）：**

| 服務 | Port | 核心 |
|------|------|------|
| caddy | 7000 | reverse proxy 入口 |
| cloudflared | — | tunnel |
| accounting | 5000 | autoQuotes |
| sqlgate | 4000 | cwsoft-sqlgate |
| otp-server | 4001 | cwsoft-sqlgate |
| bind-server | 4002 | cwsoft-sqlgate |
| clerk | 5001 | cwsoft-clerk |
| kbcs | 6004 | cwsoft-ai-customer-service |
| cs-admin | 6005 | cwsoft-ai-customer-service |
| aquan-manager | 6000 | cwsoft-aquan-manager (GTB) |
| cs-shadow | 6003 | cwsoft-ai-customer-service (GTB shadow) |

---

### 3. cwsoft-super-manager 建置

**決策：** 建立獨立專案 `cwsoft-super-manager`（在 `cwsoft-service-manager` 複製後重命名），統一管理所有服務，並擴充為「服務管理 + 專案狀態統整」雙功能。

**已建置：**
- `services.json`：11 服務完整設定（cmd、cwd、port、health_type、startup_order）
- `manager.py`：spawn / health check (HTTP/TCP/process) / auto-restart（失敗 10s 後重啟，連續 5 次停止）
- `app.py`：Flask port 9000，API：`/api/status`、`/api/restart/<name>`、`/api/stop/<name>`、`/api/start/<name>`、`/api/logs/<name>`
- `templates/dashboard.html`：深色 Web UI，5s 自動更新，含服務狀態徽章與手動控制按鈕

**待擴充：** `/api/projects` endpoint（讀各 Desktop repo TODO.md + git log）

**舊目錄 `cwsoft-service-manager`：** 因 VSCode 鎖定無法直接刪除，需手動執行：
```
rd /s /q "C:\Users\pos\Desktop\cwsoft-service-manager"
```

---

### 4. 跨專案 CLAUDE.md + PROJECT.md 文件標準化

**背景：** 各專案文件格式不一，autoQuotes 的 CLAUDE.md 同時混雜了 Claude 行為指引與專案技術細節。

**決策：** 統一採「CLAUDE.md 只放 Claude 行為規則 + @PROJECT.md；PROJECT.md 放專案技術內容」分離架構。

**`@PROJECT.md` 的意義：** Claude Code 的 `@` 語法會在啟動時自動載入同目錄的 `PROJECT.md`，等同 import。

**本輪已完成更新的專案：**

| 專案 | 動作 |
|------|------|
| autoQuotes | CLAUDE.md 換模板；技術內容移至 PROJECT.md |
| cwsoft-super-manager | 新建 CLAUDE.md + PROJECT.md |
| cwsoft-clerk | 新建 CLAUDE.md + PROJECT.md |
| cwsoft-liff-pages | 新建 CLAUDE.md + PROJECT.md |
| cwsoft-product-scout | 新建 CLAUDE.md + PROJECT.md |
| cwsoft-meeting-tracker | CLAUDE.md 換模板；SOP 內容移至 PROJECT.md |

---

## 本輪新增 / 更新文件

**autoQuotes**
- `generate_marketing_quote_零壹.py`（新增，一次性腳本）
- `CLAUDE.md`（更新，換標準模板）
- `PROJECT.md`（新增，技術內容從 CLAUDE.md 遷入）

**cwsoft-super-manager**
- `services.json`、`manager.py`、`app.py`（新增）
- `templates/dashboard.html`（新增）
- `CLAUDE.md`、`PROJECT.md`（新增）

**各專案**
- `cwsoft-clerk/CLAUDE.md`、`cwsoft-clerk/PROJECT.md`（新增）
- `cwsoft-liff-pages/CLAUDE.md`、`cwsoft-liff-pages/PROJECT.md`（新增）
- `cwsoft-product-scout/CLAUDE.md`、`cwsoft-product-scout/PROJECT.md`（新增）
- `cwsoft-meeting-tracker/CLAUDE.md`（更新）、`cwsoft-meeting-tracker/PROJECT.md`（新增）

---

## 待跟進

- [ ] 手動刪除舊目錄：`rd /s /q "C:\Users\pos\Desktop\cwsoft-service-manager"`
- [ ] cwsoft-super-manager：實作 `/api/projects` endpoint（各 repo TODO.md `[ ]` 數 + git log -1）
- [ ] 確認 port 6001 `/pos/*` 路由是否仍在使用
- [ ] 決定小豪數位孿生（port 6006）的 services.json 設定並啟用
- [ ] autoQuotes：行動裝置費用尚未納入 PDF 報價單（已知 bug #6）
- [ ] 確認 cs-shadow 的 shadow.db 是由哪個服務寫入
