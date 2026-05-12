# CWSoft 雙開門實作上線 × 三層架構釐清

- 日期：2026-05-08（下午～傍晚，承接同日上午紀錄）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-super-manager、cwsoft-aquan-manager、cwsoft-ai-customer-service、cwsoft-clerk、cwsoft-sqlgate、cwsoft-product-scout、cwsoft-liff-pages、digital-agent-xiaohao、autoQuotes、general-task-bot、cwsoft-linebot-service

> 接續 [2026-05-08-cwsoft-runtime-contract-and-apache-realignment.md](2026-05-08-cwsoft-runtime-contract-and-apache-realignment.md)。
> 上半天確立「leaflune 退役、整併到 Apache」策略 + RUNTIME.md 體系 + migration 文件。
> 下半天動手實作雙開門，並過程中再深化對 super-manager / Apache / nssm 三層架構的理解。

---

## 一、雙開門 Apache patch 真實上線

### 動工前授權

策略已下、計畫文件已寫，但「**到底有沒有實際讓 office 通到 my services**」user 直接點明：「還沒。我們今天做的全部是紙上工作」。

> user：「Apache config 你可以備份一份到你這 在去做改動」

授權我直接動 Apache config（這是解除 5/8 早上 PROJECT.md 寫的「邊界規則」 — 但僅限這次）。

### 實作步驟

1. **備份**：`cp` `httpd.conf` + `httpd-ssl.conf` 進
   `cwsoft-super-manager/docs/apache-config-2026-05-08/`，commit `025ff6f` 留底
2. **Read 完整 conf**：發現主 httpd.conf 還 `Listen 126`，跑 `mydomain.local:126` 的內網 redirect
   到 office.cwsoft.com.tw，不影響 patch
3. **Edit `httpd-ssl.conf`**：在現有 `/upload_file` 之後、`ErrorLog` 之前，加 7 條 ProxyPass：
   `/sqlgate/`（4000）、`/otp/`（4001）、`/sqlbind/`（4002，避開既有 `/bind_member`）、
   `/kbcs/`（6004）、`/cs/`（6003）、`/callback-aquan/`（6000，避開既有 `/callback`）、
   `/xiaohao/`（6006）。每條都附 ProxyPassReverse，banner 註解標明「2026-05-08 加入」
4. **語法測試**：`httpd.exe -t` → `Syntax OK`（兩個 module loaded warning 是既有，不關事）
5. **user RDP**：`Restart-Service Apache2.4` → `Status: Running`
6. **驗證**：5 條 curl，4 綠 1 紅
   - office `/sqlgate/ping` → 200 ✅
   - office `/otp/health` → 200 ✅
   - office `/sqlbind/health` → 200 ✅
   - leaflune `/sqlgate/ping` → 200 ✅（既有沒掛）
   - office `/health` → **503**（指向 8196 LineBot.py，後端沒服務）

### 503 發現觸發下個議題

`/health` 是同事舊 ProxyPass 規則，後端 `LineBot.py (8196)` 已死。順帶觸發 LineBot 化石清理。

---

## 二、LineBot.py 化石清理

### user 揭露

> 「LineBot.py 是現在阿全經理的前前身 已經是時代的眼淚了 可以刪掉」

至此確認阿全 LINE bot 的完整演進史：

```
LineBot.py (Apache /callback → 8196，公司主機 + 192.168.50.6)
   ↓ 第一次重構
main.py pos (general-task-bot/main.py，VS Code task「阿全總管」啟動)
   ↓ 散裝重構
gtb_dev.py + --conf pos_dev (services.json 5/7 早上的設定)
   ↓ 5/7 切到正式
gtb.py + --conf pos (現用，super-manager 管，老闆 LINE 對話進這裡)
```

### 註解掉 4 條 LineBot.py 路由

```apache
#ProxyPass /callback     https://192.168.50.6:8196/callback ...
#ProxyPass /usercallback https://192.168.50.6:8196/usercallback ...
#ProxyPass /health       https://127.0.0.1:8196/health ...
#ProxyPass /download     https://127.0.0.1:8196/download ...
```

不動：
- `/testcallback`（兩條，到 192.168.50.216 — 同事另一台機器）
- `/bind_member` `/passphrase`（5001 line_binding_server.py — 同事的）
- `/send_*` `/upload_file`（5003 push_center.py — 同事的）

> user：「其他都是同事那邊的服務 可千萬別動到」

### 留快照對照組

`docs/apache-config-2026-05-08/httpd-ssl.after-double-channel-and-linebot-cleanup.conf`
跟原始備份 `httpd-ssl.conf` 並列。未來想看「我改了什麼」直接 `diff` 兩份，commit `9814022`。

---

## 三、三層架構釐清（粽子頭比喻）

過程中 user 用一個非常精準的比喻把整個架構消化清楚。

### user 的問題：「服務放到 Apache，還需要自己再弄一個 nssm 嗎？」

### 三層獨立、互補

```
┌─────────────────────────────────────────────────────────────┐
│ Apache 443 (reverse proxy 對外 routing)                      │ ← L7 routing
└─────────────────────────────────────────────────────────────┘
                          ↓
                    路由到 127.0.0.1:port
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend Flask app（spawn / 跑 / crash 自動重啟 / log）       │ ← process layer
└─────────────────────────────────────────────────────────────┘
                          ↑
                    誰管它生死？
                          ↑
┌─────────────────────────────────────────────────────────────┐
│ Process supervisor：nssm / Windows Service / supervisord     │ ← supervisor layer
└─────────────────────────────────────────────────────────────┘
```

**Apache 不管 backend process 生死** — 它只做 reverse proxy。Flask 掛了 Apache 還在 listen 443，
但 proxy 失敗回 503（早上看到的 503 就是這樣）。**Backend 一定要有 process supervisor**。

公司範式實際是 **Apache + nssm**（看同事的 `line_binding_server.py` 就是用 nssm 跑），
不是 Apache 自己管 process。

### user 的「粽子頭」比喻

> 「同事是一個服務包一次 nssm，我是拿你當粽子頭，你啟動其他服務也都啟動」

精準。延伸：

```
同事模式（分散）：             user 模式（集中粽子頭）：

  nssm A → Flask A             nssm → super-manager
  nssm B → Flask B                       ├─ Flask A
  nssm C → Flask C                       ├─ Flask B
  nssm D → Flask D                       ├─ Flask C
                                          ├─ Flask D
                                          ...
```

**故障域**：
- 分散：A 死了 B/C/D 不受影響
- 粽子頭：super-manager 死了 11 個全死，但 super-manager 自己也是 nssm 跑的，crash 後幾秒被 nssm 重啟，所有 child 也重新 spawn

**控制面**：
- 分散：services.msc 看 11 條，沒統一視圖
- 粽子頭：dashboard `:9000` 一眼看 11 個，REST API 統一

**dashboard 是粽子頭模式的副產品** — 拆粽子頭就失去 dashboard。這是路線取捨的具體成本。

### user 接著問：「leaflune 退役會直接影響粽子頭嗎？」

不會直接影響。leaflune 退役 = 把對外招牌摘掉：
- cloudflared tunnel 拆（沒人連了）
- Caddy `:7000` 拆（沒貨送了）
- 粽子頭（super-manager）+ 11 顆粽子（backend Flask）+ nssm（綁繩） 一動不動
- 副作用：services.json 從 11 條變 9 條（拿掉 caddy / cloudflared）

「**routing 層遷移**」跟「**super-manager 拆粽子頭**」是兩條完全獨立的線，可以分別決策。

### 結論：短期保留 super-manager，長期再評估

短期（leaflune 還沒退役前）：
- super-manager 跟 Apache 不同層、並存零衝突
- 5/7 才花一整天接管完，現在拆等於白做
- 遷移工作主要在 routing 層，跟粽子頭結構無關

長期（leaflune 完全退役、塵埃落定後）：
- 看實際使用感
- super-manager dashboard 真的有人在用 → 保留
- 半年都沒點 → 拆成各 nssm（向公司範式靠攏）

**決策可以延到「遷完才看」，不必現在就定**。

---

## 四、阿全 log 在哪（順手釐清）

user 想知道阿全的 log 位置。三處：

| 用途 | 位置 | 大小 / 性質 |
|---|---|---|
| Process stdout/stderr（最常用）| `cwsoft-super-manager/logs/aquan-manager_(6000).log` | ~500 KB，即時寫入；dashboard「Log」按鈕讀的就是這個 |
| 業務資料 sqlite | `cwsoft-aquan-manager/database/conv_*.db` 等 | 36 KB（老闆對話歷史）+ todo/feedback/config |
| super-manager 自己 | `super-manager.{stdout,stderr}.log` | stderr 累積 4.5 MB（health check noise） |

**重點**：gtb.py 內部沒設 `logging` 模組，純用 `print()`，所有訊息都進 super-manager 收的 stdout，不散到別處。

stderr 4.5 MB 的累積觸發下個議題。

---

## 五、HEALTH_INTERVAL 從 15 秒拉長到 300 秒

### user 觀察

> 「你現在 15 秒就戳他一次，會不會太頻繁了？一分鐘我都覺得有點太多」

### 業界對照

| 場景 | 預設 |
|---|---|
| Kubernetes livenessProbe | 10 秒 |
| Docker healthcheck | 30 秒 |
| AWS ECS health check | 30 秒 |
| 原本 super-manager | 15 秒（偏激進）|

對 cwsoft 規模 15 秒太頻 — 每天每服務 5760 次 health check × 11 服務 = 6 萬+ 內部 HTTP request。

### 重要：process die 不靠 HTTP health 偵測

`monitor_loop` 順序：
```python
# 1. 先看 process poll() — die 立刻抓到
if proc and proc.poll() is not None:
    services_state[name]["status"] = "failed"

# 2. 然後才打 HTTP health check
alive = check_health(cfg)
```

真正 crash → poll() 立即偵測，不依賴 HTTP。HTTP health check 主要捕「process 還在但 hang」這種罕見情境。**health 拉長不影響真 crash 反應時間**。

### 改 300 秒（user 選 5 分鐘）

`manager.py:29` `HEALTH_INTERVAL = 15` → `300`，commit `9891c95`。

副作用：dashboard 的「最後檢查」時間最多 5 分鐘前，不是即時。要實時狀態請直接 curl backend port。

**改檔不會自動 reload Python module，等下次 super-manager restart 才生效**。本次先不主動 restart，
等下次自然要 restart 時（接管新服務、改 services.json 等）順便套用。

---

## 六、本日下半天新增 / 改動文件

### cwsoft-super-manager（5 個 commit 在本地，5/8 下半天）

| commit | 說明 |
|---|---|
| `277c4d6` | docs: migration 加雙開門 Apache patch（純 additive）|
| `ed43361` | docs: CHANGELOG 加 5/8 策略決策 — leaflune 退役整併到 Apache |
| `d79fff0` | docs: migration 加 LINE Console channel 對應 + 動工分工 checklist |
| `025ff6f` | docs: 備份 Apache config 進 docs/apache-config-2026-05-08/ |
| `9814022` | docs: Apache 雙開門 + LineBot.py 化石清理 (snapshot) |
| `9891c95` | chore: HEALTH_INTERVAL 15s → 300s（5 分鐘）|

### live 改動（不在 super-manager git 但已上線）

- `C:\Apache24\conf\extra\httpd-ssl.conf`：加 7 條雙開門 ProxyPass + 註解 4 條 LineBot.py 路由
- Apache2.4 service restart 套用

### matrix-manager

- `meetings/2026-05-08-cwsoft-double-channel-implementation-and-architecture.md`（本檔）
- INDEX.md 同步更新

---

## 七、待跟進

### 立即（routing 層遷移第一步）

- [ ] **阿全 mission_pos.json 內部呼叫改 127.0.0.1**（42 處 hits）— 不影響 LINE webhook，純效能優化
- [ ] cs mission_cs.json（3 處）+ clerk mission_store.json（2 處）同樣處理
- [ ] autoQuotes sendLineMessage.py:147 寫死 PDF URL 確認用途（hardcoded sample 還是動態）

### 中期

- [ ] LIFF 前端 `bind-membership.html` / `store-guide.html` 改 office + LINE OA Manager LIFF endpoint URL 改
- [ ] LINE OA webhook URL 從 leaflune 改 office（user RDP，5-10 min）
- [ ] super-manager 主動 restart 套用 HEALTH_INTERVAL = 300（含可能 phantom socket 風險，跟 SOP 走）
- [ ] 各 chatbot 切換完後測試 24 小時，老闆無抱怨即穩定

### 等同事確認後

- [ ] Apache 化石清查：`/testcallback` × 2 / `/bind_member` `/passphrase` / `/send_*` `/upload_file`
      實際還活著嗎？line_binding_server / push_center 還在用嗎？

### 長期（leaflune 完全退役後）

- [ ] services.json 拿掉 caddy + cloudflared（從 11 服務變 9 服務）
- [ ] cloudflared tunnel 設定拆除
- [ ] Caddy 退役
- [ ] cwsoft.leaflune.org DNS / Cloudflare 設定移除
- [ ] 評估 super-manager 是否拆成各服務獨立 nssm（路線 B）

---

## 附：當天的關鍵決策推導

### 「user 為何同意我直接動 Apache config」

5/8 早上 PROJECT.md 明確寫「super-manager 端 Claude 不該動 Apache config（同事邊界）」。
下午 user 主動說「你可以直接做嗎」，等於解除這次的邊界限制。理由：
- 純 additive 改動（不動既有任何 ProxyPass）
- 改完通知同事，事實透明
- 我有寫權限（C:\Apache24\ 不在 Program Files，user 可寫）+ 能跑 `httpd.exe -t` 測語法（不需 admin）
- restart 那條仍由 user 親自做（admin 邊界）

仍然約定「**僅這次**」 — 之後 Apache 要改回到「user 親手」default。

### 「LineBot.py 註解而不是刪」

- 註解保留歷史脈絡（將來考古「以前怎麼做」有跡可循）
- 真要刪 git history 也保得住，但既然已經沒在跑、保留 0 成本
- 如果同事看到 banner 說明「2026-05-08 註解」會立刻知道狀況

### 「health 5 分鐘是怎麼算出來的」

- 不是隨便挑的整數
- 業界範圍 10-30 秒是「需要快速 detect」的場景（k8s pod 重新調度等）
- cwsoft 規模沒這 SLA 需求 — 服務掛 5 分鐘老闆無感（LINE 自己 retry）
- 真 crash 仍由 `poll()` 即時偵測（不靠 HTTP）
- 5 分鐘是「平衡 noise + 反應時間 + log 量」的合理點

### 「粽子頭比喻為什麼那麼準」

user 自己比喻自己的架構，比 Claude 解釋更精準。隱喻三個面向：
- **形狀**：一個頭綁多個粽子 = supervisor 監管多個 child
- **動作**：一拉粽子頭一串都動 = restart super-manager 連帶 11 服務都動
- **對照**：同事是「一個一個獨立粽子」 = 各自獨立 nssm

未來其他 Claude 看到「粽子頭」就立刻 get 整個架構意圖，比技術術語還傳神。
