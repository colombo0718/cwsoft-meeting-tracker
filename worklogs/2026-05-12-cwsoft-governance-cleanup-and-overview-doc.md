# cwsoft 治理收尾 × clerk 永久下架 × OVERVIEW.md 新建

- 日期：2026-05-12（晚上，承接同日上午另一個 Claude session 的 gtb_dev 後門 + cs-shadow admin + aquan-dev 三條線）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-super-manager、cwsoft-project-tracker、matrix-manager、general-task-bot

> 承接 [2026-05-11-cs-shadow-empty-drafts-and-gtb-encoding-cleanup.md](2026-05-11-cs-shadow-empty-drafts-and-gtb-encoding-cleanup.md)
> （上次 push 卡 wincredman）。本次 user RDP 進來解 push 問題，連帶把 cwsoft 跨機治理 +
> 服務化石清理 + 公司儀表板新文件一次收尾。

---

## 一、起點：把卡住的 push 處理完

5/11 三個 commit 在 local：
- `matrix-manager`：5 commits 領先（5/7/8/8/10/11 五篇 cwsoft 會議紀錄）
- `general-task-bot`：2 commits 領先（gtb_dev.py / gtb.py 兩 fix）
- `cwsoft-super-manager`：10+ commits 領先

user RDP 進來後，credential vault 對 wincredman 通了，但**馬上踩到 MM 的 divergence**。

---

## 二、MM rebase：跨機器 INDEX.md 衝突

`git fetch` 後 MM 同時：
- 我這邊 5 commits 領先
- 笔电那邊 4 commits 領先 — **包含 a1127cd `CWSoft 解耦：20 篇 worklog 遷移至 cwsoft-project-tracker repo`**

也就是說，笔电那邊**已經把 CWSoft 區段從 MM/INDEX.md 整段移除**，本檔即將從此「只索引 LL 宇宙」。

`pull --rebase` 觸發兩個衝突：
1. **「最後更新」line**：兩邊不同日期 → 取 incoming（我的），後續 commit 會自然覆寫
2. **`cwsoft-ai-customer-service` section**：兩邊各加了一個 5/7 紀錄（`cwsoft-customer-service-sop.md` vs `cwsoft-services-takeover-via-super-manager.md`） → **兩個都保留**

Rebase 通過、push 成功。MM 從此正式進入「LL-only」狀態。

---

## 三、cwsoft 工作紀錄 routing 確立

MM pull 後**又卡住一次** — local INDEX.md 還有變動 + 3 個 5/12 cwsoft 檔在 `meetings/`：

```
meetings/2026-05-12-aquan-tier-classifier-prep-for-backdoor.md
meetings/2026-05-12-cs-shadow-admin-remote-auth-and-ux.md
meetings/2026-05-12-gtb-dev-backdoor-and-aquan-dev-service.md
```

**這些是另一個 Claude session 寫的，按新政策該住 cwsoft-project-tracker**。診斷一查 —
**三個檔早就同時放在 cwsoft-project-tracker/worklogs/ 也是 untracked**（另一個 session 同時放兩邊）。

`diff -q` 確認兩邊 byte-identical → 從 MM 刪除安全。

處理流程：
1. 刪 MM `meetings/` 的 3 個檔
2. `git checkout -- INDEX.md`（local CWSoft 區段索引改動丟棄，反正 remote 整段砍）
3. MM `git pull --ff-only`
4. cwsoft-project-tracker 那邊 commit + push 3 個 worklog（commit `cdf2ac6`）

### Memory entry 同步建立

把這條 routing 規則進 memory：

```
~/.claude/projects/c--Users-pos-cwsoft-super-manager/memory/repo_worklog_routing.md
```

未來 Claude 開新 cwsoft session，第一輪就會知道 worklog 該寫進 cwsoft-project-tracker，
**不會再誤寫 MM**。

---

## 四、cwsoft-super-manager 首次上 GitHub

super-manager 從沒設過 remote — 10+ commit 全 local（5/7 接管 / 5/8 雙開門 / 5/10 vision.md
等）。user 提供 `https://github.com/colombo0718/cwsoft-super-manager`，第一次 push -u 全部歷史上去。

**順帶提醒**：repo 內含 oa_registry.json 路徑、Apache config snapshot、服務拓樸，要去
GitHub 設 **private**（雖然 .gitignore 擋掉實際 token，內部結構不宜公開）。

---

## 五、clerk 服務永久下架

### 發現 clerk 是孤兒

user 問「clerk 在做什麼」，順手 audit：
- **設計**：排程管理 API（書記，Flask + SQLite，提供 `/schedule/create|list|done|cancel` 等 GET endpoint）
- **預期被誰用**：GTB / aquan-manager 集中存排程任務
- **實際**：grep 全 cwsoft Desktop — **除了 clerk 自己沒任何 .py 提到 clerk / 5001 / `/schedule/`**
- **schedule.db 最後寫入**：2026-01-30（4 個多月 dead）

為什麼孤兒：GTB 自己用 `database/todo_list.db` 做排程（gtb.py:108），**從來沒走 clerk** —
clerk 是「設計時想做集中排程，但 GTB 直接內建版本，clerk 從此被繞過」。

### 下架動作

執行清理（每步都 verify 才下一步）：

1. `POST /api/stop/clerk%20(5001)` → super-manager 回 stopped；5001 port 上的 clerk PID 釋放
2. `services.json` 移除 clerk block
3. Caddyfile 移除 `handle_path /clerk*` 區段
4. `caddy validate` → ok，`caddy reload` → ok
5. `nssm restart cwsoft-super-manager` → 新 services.json 生效；API count 從原本 12（含 clerk + 今早新加的 aquan-manager-dev）變成 11
6. PROJECT.md：刪 clerk reference card、A 類表移除、F 類加註「2026-05-12 下架」
7. TODO.md：「釐清 5001 第二個 listener 身份」改 ✅ + 結論註記

### 5001 port 撞 listener 之謎也順手解了

5/7 接管時提的「5001 同時被 cwsoft-clerk + line_binding_server.py listen」現在收尾：
- 同事 nssm 跑的 `line_binding_server.py` (PID 52256) 是 5001 真實 owner
- clerk 是後到、被 line_binding_server 擠著的 second listener
- clerk 下架後 5001 從此只剩 line_binding_server，邊界清楚

clerk repo（`C:\Users\pos\Desktop\cwsoft-clerk\`）跟 schedule.db **保留為化石**，不刪 — 將來
如果某天又想做集中排程可以參考。

---

## 六、回顧 cwsoft-h2-2026-direction.md + 確立三層文件

user 把焦點切到「下半年大方向」這份 5/12 老闆對焦會議萃取出來的檔。

問題：cwsoft-project-tracker repo「不能只是塞一堆會議跟工作紀錄」，**需要一個當下狀態彙整**
— 像 MM 有 `UNIVERSE.md` 做整個 LL 生態的儀表板那樣，cwsoft 也該有一份。

### 檔名抉擇

UNIVERSE 是 LL「個人創業多平台生態」的詩意稱呼，cwsoft 不能照搬。

候選對比：

| 檔名 | 對位 | user 評 |
|---|---|---|
| `LANDSCAPE.md` | 公司全景 + 商業景觀雙重語感 | — |
| `MAP.md` | 老闆「那張圖」直譯 | 跟「樹狀架構圖」會搞混 |
| `ATLAS.md` | 圖集 | 少動態感 |
| `OVERVIEW.md` ⭐ | 樸實直白 | **「直白」— user 選**|

### 三層文件層級確立

| 文件 | 範圍 | 對誰 | 住哪 repo |
|---|---|---|---|
| `cwsoft-vision.md` | 1-3 年戰略 north star | Claude 工作前 context | super-manager |
| `cwsoft-h2-2026-direction.md` | 6 個月具體走法 | Claude + 老闆 | super-manager |
| **`OVERVIEW.md`**（新）| **公司當下儀表板** | **老闆 / 同事 / 新進 AI** | **cwsoft-project-tracker** |

**關鍵分界**：
- super-manager = 「給 Claude 工作的戰略 context」— vision / direction 都在這
- cwsoft-project-tracker = 「給人類（老闆 / 同事）+ 新進 AI 的公司面對外文件」— OVERVIEW 在這

這對應到 5/12 解耦的同一個原則：**LL 個人 / cwsoft 公司 治理分離；公司面對外用 cwsoft-project-tracker，公司內部技術細節用 super-manager**。

---

## 七、OVERVIEW.md 草稿（176 行，9 段）

骨架：

1. **一句話定位** — 上半年技術底盤 / 下半年請客戶走 + 翻譯老闆詞
2. **服務體系** — 按誰受益分（A 老闆自用 / B B2B 門市 / C C 端消費者 / F 已下架）
3. **資訊部三大主軸** — KPI / GTP × Codex / 命名整頓
4. **里程碑時間軸** — 5/9 已過 / 5/16 羿宏返國 / 6/1 零壹進階行銷 / 6 月口試 / 年底 10% / 2027 50-80%
5. **客戶專案儀表板** — 連 README.md PROJECT_STATUS，不複製
6. **人員 + AI 同事分工** — 彥偉/士豪/羿宏 + Claude/Codex/Cursor
7. **技術底盤簡要** — 11 服務 / Apache+Caddy+cloudflared 三層 / 雙通道過渡
8. **業務面備忘** — 月租化、新功能優先、新威 12 點訊息
9. **維護備忘** — 每月輪值更新 / 里程碑前後即時更新

### 寫完後抓到兩個錯：羿宏 5/9 出國，不是 5/16

user 看完抓兩個 bug：
1. 出國的是**羿宏**，不是士豪（h2-direction.md 第 3 行原本寫「士豪 5/16 出國前的密集對接」也錯）
2. 日期是 **5/9 出國、5/16 回**（不是 5/16 出國）

→ 修：
- `h2-direction.md:3` 改成「羿宏 5/9 出國、5/16 回國期間的對焦」
- `h2-direction.md:219` 拿掉「（羿宏？）」的問號
- `OVERVIEW.md:92-93` 時間軸拆兩列：5/9 已過（刪除線）+ 5/16 羿宏返國

時間錯認的根因：h2-direction.md 是上一個 session 從會議逐字稿萃取的，**逐字稿時間描述含糊**
（「飛機走之前」），萃取時誤合到「5/16 出國前」這個錯誤 framing。修完後事件序變正確：
**5/9 出國 → 5/12 老闆 × 士豪 對焦（羿宏不在）→ 5/16 羿宏返國**。

---

## 八、本日成果

### cwsoft-super-manager
- 首次 push 上 GitHub（`colombo0718/cwsoft-super-manager`，建議設 private）
- **clerk 服務永久下架** — services.json / Caddyfile / PROJECT.md / TODO.md / nssm 五處同步清理
- `h2-direction.md` 兩處校正（羿宏 5/9 出國、attribution 修正）

### cwsoft-project-tracker
- 新檔：`worklogs/2026-05-12-{aquan-tier / cs-shadow-admin / gtb-dev-backdoor}.md`（3 篇，從 MM 遷移，`cdf2ac6`）
- **新檔：`OVERVIEW.md`**（176 行公司儀表板）
- 本檔 worklog

### matrix-manager
- pull 同步 + rebase + push（解 INDEX 兩處衝突）
- CWSoft 區段從此正式退場，本 repo 只索引 LL 宇宙
- 3 個 5/12 cwsoft 檔遷出

### general-task-bot
- push 5/11 兩個 commit 到 origin

### Claude memory
- 新增 `repo_worklog_routing.md` — 未來 cwsoft worklog 寫對 repo 不會再混淆

---

## 九、待跟進

### 立即
- [ ] super-manager GitHub repo 去設成 **private**（含 oa_registry 路徑等敏感結構）
- [ ] commit + push 本次 super-manager 改動（clerk 清理 + h2-direction 校正）

### 短期
- [ ] **進入 DR 主題**：公司主機掛了能在老闆家 server 5-15 分鐘內復原全套服務 + 對外接口完全一致 — 已開始討論，下篇 worklog 主題
- [ ] OVERVIEW.md 跟 README.md 的銜接：要不要在 README 開頭加指向 OVERVIEW 的導引

### 中期
- [ ] OVERVIEW.md 每月一次輪值更新（首次正式更新建議 6/2，零壹上線後第一個工作日）
- [ ] 11 服務樹狀架構圖（老闆會議要的「進公司第一天 AI 帶你看的那張圖」） — 預計畫進 OVERVIEW 或獨立檔

---

## 附：當天的關鍵推導

### 「為什麼 INDEX.md 衝突有兩處不同處理」

第一處（最後更新日期）：兩邊**互斥**，取一個即可 — 取 incoming（後續 rebase 步驟還會覆寫）。
第二處（cwsoft-ai-customer-service 各加一個 5/7 檔）：兩邊**互補** — 都該保留。

教訓：rebase 衝突要先判斷是「互斥替換」還是「互補疊加」，不要一律 take ours / theirs。

### 「為什麼 clerk 留 4 個月沒人發現」

兩個累積條件：
1. clerk 本來就是「設計後沒人接」— GTB 內建排程是後續決定，clerk 直接被繞過但沒人正式宣告下架
2. health check 一直綠燈（5001 port 通 = OK），dashboard 看不出「無流量」狀態

教訓：**process 活著 ≠ 業務邏輯活著**。super-manager dashboard 該補一個「最後 X 天有沒有真實流量」指標，否則 silent unused 服務會繼續累積。

### 「為什麼 cwsoft 解耦對 AI 工作很重要」

5/12 之前的 matrix-manager 同時收 LL 個人創業 + cwsoft 公司工作 — 對「對外」場景很危險：
- 老闆要看 cwsoft 進度，AI 帶他看 MM 會掃到 LL 未簽約商業內容
- 教同事方法時給 MM repo，邊界不清

解耦後 cwsoft-project-tracker 是「公司面 facade」，super-manager 是「資訊部技術 backend」，
matrix-manager 退回「個人 / LL 治理層」— 三 repo 各司其職、AI 進來邊界清楚不亂跨。
