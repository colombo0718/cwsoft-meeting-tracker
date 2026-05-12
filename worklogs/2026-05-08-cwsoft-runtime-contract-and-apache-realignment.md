# CWSoft 跨 Claude 協作契約 × Apache 整併策略決定

- 日期：2026-05-08
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-super-manager、cwsoft-aquan-manager、cwsoft-ai-customer-service、cwsoft-clerk、cwsoft-sqlgate、cwsoft-product-scout、cwsoft-liff-pages、digital-agent-xiaohao、autoQuotes、general-task-bot、cwsoft-linebot-service、matrix-manager

---

## 一、5/7 接管成果驗證（過第一夜）

5/7 中午 cwsoft 全服務接管 + super-manager 上 nssm 後，今早查當前狀態：

- super-manager dashboard 11/11 全綠
- **PID 跟昨天 12:13 截圖完全一樣** — 22 小時沒有任何重啟
- 過了第一次「IDE 完全脫離」+「過夜」+ user 重啟 VS Code 的考驗

「印度電工終結」的 nssm 化方案經過實戰過夜驗證有效。

---

## 二、product-scout pipeline 跑通

**背景**：cwsoft-product-scout 是手機商品爬蟲 pipeline，老闆預期每日定時跑一次，
但實際從沒設過 Task Scheduler，4 個月沒 commit，user 都是「想到才手動跑」。

### 第一次跑：fail 在 step 6（merge）

跑 54 分鐘後撞 `UnicodeEncodeError: 'cp950' codec can't encode '\xb6'`。

**根因**：`mergeData.py` line 199-214 用 `print()` 印含中文 dataframe，
Windows console 預設 cp950 不能處理某些 Unicode 字符（拉丁特殊字、全形符號等）。
這是 Windows + Python + 中文資料的典型雷。

### 修法：拿掉 debug print

那段 print 是開發者 debug 殘留（pric_best / land_best / sogi_best 各 print 一次），
production 不需要。直接刪 16 行解決。

### 第二次（後半部）：1 分鐘跑完

- 不重爬，從 step 6 接續：merge → summarize → update db → update source
- DB 真實寫入：`PublicProduct_Source` 新增 23 筆（OPPO FindN6 / vivo X300Ultra /
  realme 16 / 小米 平板Pad29.7 / Benten F72 / iPhone17e 粉 等新機型/新色號）
- 確認 pipeline 邏輯堪用，**欠的是 Task Scheduler 化 + logging hardening**

### 通用學到（補進 super-manager docs）

**Python script 在 Windows scheduled task 跑時必設環境變數**：
- `PYTHONIOENCODING=utf-8` — 強制 stdout 用 utf-8，避開 cp950 雷
- 跟 nssm 環境變數踩坑（PATH/APPDATA/PYTHONPATH/USERPROFILE/HOME）是同類別問題

---

## 三、PROJECT.md 大整理（流水帳搬走）

user 觀察：「PROJECT.md 太多流水帳」（5/7 寫完接管紀錄後，PROJECT.md 372 行，其中 180 行
是「按時間記錄發生什麼」的流水帳）。按 CLAUDE.md 規範，里程碑該進 CHANGELOG.md，
PROJECT.md 留「現況 + 重複可用的東西」。

### 重整：372 行 → 252 行

**砍**：
- 「接管紀錄 5/7 早上」（52 行 OTP/bind 細節）
- 「接管紀錄 5/7 中午」（105 行全接管 + nssm 細節）
- 「接管中（待做）」（11 行過時清單，內容已執行完成）

**搬**：濃縮成 CHANGELOG.md 兩條里程碑（4/27 建立、5/7 全接管）。

**補強**：
- 服務清單從短表格升級成「reference card」格式（11 個服務每個一張卡，
  含 cmd / cwd / health / 對外 URL / 依賴關係 / dev/prod 對照 / 已知 quirk）
- 加「Service spawn 環境」section（5 個 nssm AppEnvironmentExtra 變數含義）
- 「接管 SOP」整合 D 類雷（健檢假陽性 / 舊 process 騙過 health / phantom socket）

### 創 CHANGELOG.md（新檔）

兩條里程碑紀錄。連到 matrix-manager 對應會議紀錄（細節想看就跳過去）。

---

## 四、跨 Claude 協作機制：RUNTIME.md 體系

### 問題

cwsoft 服務跑在 super-manager 下，但程式碼在各服務自己的 repo（cwsoft-aquan-manager
跑 GTB 引擎、cwsoft-sqlgate 三個 service 各一支 .py 等）。當其他 Claude 在某 repo
工作時：
- 沒辦法直接跟 super-manager 端的 Claude 溝通（沒 MCP）
- 但又需要知道「我被怎麼啟動」、「我改了啟動方式要怎麼通知對面」

user 的 framing：「應該不太能直接 MCP 之類的跟你溝通吧」。

### 解法：契約模式（不是申請模式）

每個服務 repo 維護一份 `RUNTIME.md` — 程式作者**主動聲明**「我希望被這樣跑」。

**契約 vs 申請** 的選擇：
- 申請（被動：「我改了 X，請你看看」） → 容易被遺忘、累積 backlog
- 契約（主動：「我的執行規格就是這樣」） → super-manager 端 Claude 任何時候進來都看得到、且是真理
- 申請暗示「super-manager 是裁判」，契約暗示「**服務作者最懂自己**」 — 後者更符合事實

衝突時以 RUNTIME.md 為準（不是 services.json）。

### 為什麼獨立 .md 不塞 PROJECT.md

- **語意分離**：執行契約是獨立 concern，跟「這專案是什麼」混在一起會稀釋兩邊
- **變更歷史**：`git log RUNTIME.md` 純契約演化，不混 PROJECT.md 的其他改動 noise
- **機械化驗證容易**：未來 super-manager 寫 `validate_contracts.py` 直接讀整檔就好
- **「檔案存在這件事本身就是個聲明」**：super-manager 端 Claude 看到某 repo 沒
  RUNTIME.md → 知道「這個還沒準備好被接管」

### 三種 deployment_mode

範本支援三種：
- **resident**：常駐 long-running service，super-manager spawn / monitor / restart
- **scheduled**：定時 pipeline（例如每日爬蟲），由 Windows Task Scheduler 觸發；
  super-manager 不 spawn，只「觀察」最近執行紀錄
- **external**：外部部署（Vercel / Cloudflare Pages 等），super-manager 只
  「驗證可達性」（打 deploy URL 看 200）

### 實作（Phase A 規範 + Phase B 各 repo）

**Phase A**（super-manager 端）：
- `CLAUDE.md` 加 RUNTIME.md 進通用檔案規範表 + 寫作規範段
- `PROJECT.md` 加「跨 repo 協作機制」section
- `docs/runtime-contract-template.md` 範本（self-contained，cp 即用）

**Phase B**（8 個 RUNTIME.md，由 Claude 一次幫忙寫好）：

| repo | mode | 說明 |
|---|---|---|
| autoQuotes | resident | accounting (5000) — 老闆儀表板 |
| cwsoft-sqlgate | resident | 一份 RUNTIME.md 列 3 個 service（sqlgate / otp / bind）|
| cwsoft-clerk | resident | clerk (5001) |
| cwsoft-ai-customer-service | resident | 一份 RUNTIME.md 列 3 個 service（kbcs / cs-admin / cs-shadow）|
| cwsoft-aquan-manager | resident | aquan-manager (6000) — 阿全 critical path |
| digital-agent-xiaohao | resident | xiaohao (6006) — 待接管 |
| cwsoft-product-scout | **scheduled** | 每日 pipeline，無 Task Scheduler 待設 |
| cwsoft-liff-pages | **external** | Vercel 部署 |

三種 mode 都有具體實例 — 不是空談範本，是真實在運作。

未來各 repo 自行維護 RUNTIME.md。改本檔時可在 MM 會議紀錄帶 `🔧 需 super-manager 同步` tag。

---

## 五、cwsoft 體系全景表（PROJECT.md 加 6 類）

| 類別 | 部署模式 | 範例專案 | super-manager 顯示 |
|---|---|---|---|
| **A** | 常駐已接管 | autoQuotes / cwsoft-sqlgate / cwsoft-clerk / cwsoft-ai-customer-service / cwsoft-aquan-manager / general-task-bot | 健康狀態 + PID + 重啟次數 |
| **B** | 常駐待接管 | digital-agent-xiaohao | 標警示「未在 services.json」 |
| **C** | 外部部署 | cwsoft-liff-pages（Vercel）| URL 可達性 + 最後 deploy 時間（未來）|
| **D** | 定時 pipeline | cwsoft-product-scout（待設 Task Scheduler）| 上次執行時間 + 結果（未來）|
| **E** | 工具型 repo | cwsoft-meeting-tracker / cwsoft-super-manager 自己 | 不該出現在 dashboard |
| **F** | 待清理 | cwsoft-linebot-service / cwsoft-bot-boot.bat | 拆除（避免有人誤觸召喚舊架構）|

這份分類也是未來 `/api/projects` endpoint 的資料骨架。

---

## 六、重大發現：Apache 平行體系

user 提示去看 `C:\Apache24\conf\extra\httpd-ssl.conf`，發現：

### 公司主機上有兩條獨立對外通道

```
通道 1（user 之前盤點過、super-manager 管的）:
  cloudflared tunnel  →  caddy :7000  →  11 個 cwsoft 服務
  domain: cwsoft.leaflune.org

通道 2（5/8 才發現）:
  Apache 2.4 :443 (Windows Service, Automatic 自啟)
  domain: office.cwsoft.com.tw（真實 SSL cert）
  →  ProxyPass 到 4 個後端：
       - port 8196  LineBot.py        (LINE webhook handler，舊版)
       - port 5003  push_center.py    (LINE 訊息推送 API)
       - port 5001  line_binding_server.py  (nssm Service，給 /bind_member /passphrase)
       - 192.168.50.216:* （另一台機器！）
```

之前 5/7 接管 cwsoft 體系時完全沒抓到這條線。我（Claude）跟著 cloudflared/Caddy
鏈走，沒發現公司主機上還有獨立的 Apache 在 443 跑。

### 5001 第二個 listener 的真相揭曉

5/7 接管時發現 5001 有兩個 listener（cwsoft-clerk + 神秘的 line_binding_server.py），
當時列為「待釐清的 mystery」。今天 Apache 的 ProxyPass 揭曉：line_binding_server 是
Apache 路由 `/bind_member` `/passphrase` 的後端。

---

## 七、user 揭露關鍵脈絡

> 「Apache 這一系列是同事建置好的環境，但不知道為甚麼我 Apache 印象不好潛意識在
> 抗拒，然後就自己探索琢磨出 cloudflared 這一套」
>
> 「Apache 這一套才是符合公司要的範式，應該是要整合上去」
>
> 「leaflune.org 也是我自己買來創業的網域」
>
> 「只是現在有一些我負責的 lineoa 的 webhook 還連在 CF 上，怕一改有些東西又掉了」

這完全顛倒了我（Claude）對 cwsoft 體系的理解。

### 重新認識 super-manager 的定位

| | 我（Claude）原本以為 | 事實上 |
|---|---|---|
| 主體系 | cwsoft.leaflune.org（cloudflared + Caddy + super-manager） | office.cwsoft.com.tw（Apache + nssm，公司範式）|
| super-manager 角色 | cwsoft 全體系中央指揮 | **user 個人探索那套**的管理工具 |
| Apache | 「老舊平行」 | 公司正規 |
| leaflune.org | 公司網域之一 | **user 個人買的，原本要做個人創業專案**（leaflune 生態系）|

cloudflared/leaflune 不是「主」，而是 user 個人探索的「平行宇宙」。Apache 才是公司
正規。super-manager 是 user 自己玩的那套的管理工具，不是 cwsoft 全體系中央。

巧合的是，兩套的「process supervisor 思維」最終是一樣的（都是 nssm + Windows
Service），user 獨立摸索出來的東西沒走偏，只是用了不同的工具鏈（Apache reverse
proxy vs Caddy）。

---

## 八、策略決策（記入 super-manager CHANGELOG.md）

確立 cwsoft 對外通道長期方向：

### 過渡期：兩通道並行

避免一次切換大規模掉服務。LINE OA Manager 改 webhook URL 是 fragile 動作（每改
一個就有掉服務的風險），不能 proactive 大遷移。

### 終態

- `cwsoft.leaflune.org` 完全退役，所有 cwsoft 服務統一走 `office.cwsoft.com.tw`
- `leaflune.org` 回歸個人專案使用（leaflune 生態系：LeafLune / ReinforceLab /
  DataDojo / TradeTrail 等）
- super-manager 角色不變：仍管 11 個本地 spawn 服務的生命週期，遷移時把對外路徑
  改到 Apache（Apache 加 ProxyPass）

### 動手節奏

依 [docs/leaflune-to-office-migration.md](https://github.com/colombo0718/cwsoft-super-manager/blob/master/docs/leaflune-to-office-migration.md) 5 階段 checklist，被動 trigger 為主：
- 某 OA 自然要改設定 → 順便改 webhook URL
- cloudflared / leaflune 出狀況 → 被迫遷
- 整體決策退役 → 系統性遷移

---

## 九、leaflune→office migration 文件

完整盤點 cwsoft.leaflune.org 寫死的 84+ hits 散在 13 個檔案：

### 真實要動 51 處

| 類別 | 檔案 | hits |
|---|---|---|
| 阿全 mission | `mission_pos.json` + `mission_pos_dev.json` | **42** |
| cs mission | `mission_cs.json` | 3 |
| clerk mission | `mission_store.json` | 2 |
| autoQuotes | `sendLineMessage.py` | 1 |
| LIFF 前端 | `bind-membership.html` + `store-guide.html` | 3 |
| LINE OA webhook | LINE OA Manager 設定（不在 code，要 RDP）| — |

### 不該動 33+ hits

- `worker.leaflune.org`（個人 LLM worker，不在公司範圍）
- sqlgate CORS 白名單（是 allow origins 不是 API 入口）
- `general-task-bot/` 自己根目錄的舊 mission（散裝模式不讀，monolithic 殘留）
- 各 PROJECT.md / README.md / RUNTIME.md / 文件（事實記錄，最後才更新）
- `database/*.db` 內含 URL（對話歷史，動了破壞紀錄）

### 核心 insight：內部呼叫應該走 127.0.0.1

阿全跟 sqlgate 在**同一台主機**，但目前每次 `/sqlgate/query_points` 都繞：

```
chatbot → cloudflared → CF edge → 回本機 → caddy → sqlgate
```

改 127.0.0.1 直連 = 跳過所有 reverse proxy。效能更好、不依賴外網穩定性。
只有 LIFF 前端跟 LINE webhook 才需要公網 URL — 那部分才需要 office + Apache ProxyPass。

### 動工分工

- **Claude 90% 代管**：本地檔案 + LINE 公開 API（LIFF endpoint URL / Messaging /
  Rich Menu）
- **user 10% 必做**：LINE Developer Console 沒公開 API 的部分（webhook URL /
  channel secret / access token）

5 階段 checklist 把 user 動作收斂到 30-50 分鐘。

### LINE Developer Console 6 channel 對應地圖

從 console 截圖看到 6 個 channel：
- 全葳小助手 → aquan-manager (6000) `@708juxdz` ✅
- 會員綁定 → LIFF 綁定流程 ✅
- 全葳 liff 網頁 → LIFF 多頁面 ✅
- 全葳智慧門市 → ⚠️ 待釐清
- 記帳助理 → ⚠️ 待釐清
- 全葳軟體資訊有限公司 → ⚠️ 待釐清（可能屬 Apache 舊體系不該動）

---

## 十、本日新增 / 更新文件

### cwsoft-super-manager（共 10+ commits 待 push）

| 檔案 | 改動 |
|---|---|
| `PROJECT.md` | 大重整：流水帳搬走、服務清單升級為 reference card、加全景表 + 兩個對外通道宣告 |
| `CHANGELOG.md` | 新建 + 加三條里程碑（4/27 建立、5/7 全接管、5/8 策略決策）|
| `TODO.md` | 大幅補充未來事項（含 L3 variant、桌面搬家、SOP 改進等）|
| `CLAUDE.md` | 加 RUNTIME.md 進通用檔案規範表 |
| `docs/runtime-contract-template.md` | RUNTIME.md 範本（self-contained）|
| `docs/leaflune-to-office-migration.md` | 完整 51 處遷移清單 + 6 channel 對應 + 動工分工 |
| `docs/nssm-python-service.md` | 5/7 寫的，5/8 維持 |
| `setup-nssm.cmd` | 5/7 完整版（5 個環境變數）|
| `services.json` | 5/7 改動，5/8 不動 |

### 各服務 repo 各自的 RUNTIME.md（8 個）

- ✅ commit：autoQuotes / cwsoft-sqlgate / cwsoft-clerk / cwsoft-ai-customer-service / cwsoft-product-scout / cwsoft-liff-pages
- ⚠️ 留本地（repo 沒上 git）：cwsoft-aquan-manager / digital-agent-xiaohao

### cwsoft-product-scout

- `mergeData.py` 拿掉 line 199-214 dataframe debug print（修 cp950 雷）— 已加進 git status，待 commit

### matrix-manager

- 本檔 `meetings/2026-05-08-cwsoft-runtime-contract-and-apache-realignment.md`
- INDEX.md 同步更新

---

## 十一、待跟進

### 立即（user 有空就做）

- [ ] **LINE Developer Console 6 channel webhook URL 盤點**（10 分鐘 RDP）— 看每個 channel 當下 webhook URL，補完 migration 文件的 channel 對應地圖。**零風險、無系統改動**
- [ ] **super-manager + 7 個 repo commit push 上 GitHub**（RDP 一次處理完所有 ahead commits）
- [ ] cwsoft-product-scout `mergeData.py` 改動 commit（小 patch）

### 短期

- [ ] 設 SSH key 一勞永逸解 wincredman 問題（之後 push 不用 RDP）
- [ ] cwsoft-aquan-manager / digital-agent-xiaohao / autoQuotes 上 git
- [ ] product-scout 設 Task Scheduler 真實每日跑（含 PYTHONIOENCODING=utf-8 環境變數）

### 中期

- [ ] **小豪 (xiaohao 6006) 上線時直接設 office** — 第一個建立 `/callback-<bot>/` Apache ProxyPass 模式
- [ ] cs-shadow / line_binding_server / LineBot.py 三者關係釐清（第二體系內部）
- [ ] 拆 cwsoft-linebot-service 舊 workspace + cwsoft-bot-boot.bat
- [ ] 改各 chatbot mission_*.json 內部呼叫為 127.0.0.1（不需要 LINE 後台動的部分）

### 長期

- [ ] LIFF 前端遷 office + LINE OA Manager 改 webhook URL（user 必做）
- [ ] L3 variant 切換實作（dashboard 一鍵 dev↔prod）
- [ ] super-manager `/api/projects` 實作（按 A/B/C/D/E 類分別顯示資料）
- [ ] 各服務補真 `/health` endpoint（取代當前的 lucky pass）
- [ ] cwsoft.leaflune.org 整體退役 → leaflune.org 完全回歸個人專案

---

## 附：當天的關鍵決策推導

### 「為什麼把 RUNTIME.md 獨立 .md 而不塞 PROJECT.md」

語意分離（執行契約是獨立 concern）+ 變更歷史純（`git log RUNTIME.md` 不混 noise）
+ 機械化驗證容易（未來 `validate_contracts.py` 直接讀整檔）+「檔案存在這件事本身就是個聲明」。

### 「契約模式 vs 申請模式」

契約 = 主動聲明事實（程式作者最懂自己），申請 = 被動等對方看。前者讓 super-manager
端 Claude 任何時候進來都看得到，且是真理；後者容易遺忘、累積 backlog。

### 「為什麼整併方向是 leaflune → Apache 不是反過來」

Apache 是公司範式（同事建、運行多年、符合公司治理慣例）；leaflune 是 user 個人探索
（自買網域、原本要做個人創業）。整併要回歸正規。

### 「為什麼 migration 用被動 trigger 而非 proactive」

LINE OA webhook 改 URL 是 fragile 動作（每改一個就有掉服務的風險），老闆每天用阿全
不能輕易動。被動 trigger（OA 自然要改設定 / cloudflared 出狀況 / 整體退役）才動，
配合 30-50 分鐘 user 動作 checklist。

### 「為什麼 mergeData.py 是拿掉 debug print 不是改 PYTHONIOENCODING」

那段 print 是開發者 debug 殘留，**production 不需要**。拿掉 = 真正的根因解決。
PYTHONIOENCODING=utf-8 是「保險」（避免別處還有類似 print），但根因是「不該有 debug
print 在 production code」。
