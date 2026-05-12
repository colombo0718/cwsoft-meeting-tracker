# cs-shadow admin UI 遠端認證 × 通知 / RWD / UX 整體優化

- 日期：2026-05-12（下午～傍晚，承接同日上午 gtb_dev 後門 + 中午老闆對焦會議）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-ai-customer-service、cwsoft-super-manager

> 承接 [2026-05-12-gtb-dev-backdoor-and-aquan-dev-service.md](2026-05-12-gtb-dev-backdoor-and-aquan-dev-service.md)
> 跟 [cwsoft-meeting-tracker/meetings/會議記錄_2026-05-12.md](C:/Users/pos/Desktop/cwsoft-meeting-tracker/meetings/會議記錄_2026-05-12.md)。
> 中午跟老闆對焦會議拍板「遠端認證 4 點 deadline」，下半天動手把 cs-shadow admin UI 從「內網管理用」變成「老闆手機 / 家裡電腦可用」。途中順手修了一堆 UX 細節。

---

## 一、起點：老闆要 4 點前能用

中午對焦會議上老闆原話「彥偉今天目標：4 點前若能做出來，就不必再到公司」。需求：
- 手機 + 家裡電腦能存取影子模式（不必裝 LINE OA 也能看訊息，避免「讀掉了客戶就漏」）
- 認證方式參考遠傳業務員地後台：**鎖 IP + 鎖憑證**
- 認證期限半年

跟 user 對齊三個分叉，拍板**分兩階段**：
- **v1（4 點前）**：cookie session + 帳密登入，先讓網址能用
- **v2（晚一點）**：補 IP 白名單 + mTLS client cert

---

## 二、auth 一波三折

### Step 1：Caddy basic_auth（30 分鐘做完，但手機掛掉）

最初設計：Caddy `basic_auth` directive + bcrypt hashed password。

```caddyfile
handle_path /admin/cs/* {
    basic_auth {
        boss $2a$14$...hashed...
    }
    reverse_proxy 127.0.0.1:6005
}
```

對 admin/app.js 跟 admin/index.html 做了配套：
- `<base href="./">` 處理 link/script 相對解析
- app.js fetch 從 `/admin/...` 改 `admin/...`（去掉 leading slash）
- 圖片 `<img src="admin/image/...">` 也改相對

CLI 端 curl 測四個 case 全綠：沒帶 auth 401 / 錯密碼 401 / 對密碼 200 / static 跟 API 路由都通。**訊息給老闆**。

### Step 2：老闆手機回報 `ERR_HTTP_RESPONSE_CODE_FAILURE`

老闆即時截圖回來，Chrome Android 顯示 `net::ERR_HTTP_RESPONSE_CODE_FAILURE`。**user 即時收回訊息**。

抓 root cause：Cloudflare CDN + cloudflared tunnel 對 Chrome Android 走 HTTP/3 時，**Basic Auth 401 + WWW-Authenticate + Content-Length: 0** 這個組合會被 Chrome 判定為 malformed response。已知 compatibility issue。

### Step 3：改 Flask cookie session

把 auth 從 Caddy 拿掉，整個搬到 Flask 端：

- Caddy 退回純 `reverse_proxy 127.0.0.1:6005`
- admin_server.py：
  - `app.secret_key`（存 `.admin_secret` 檔，cross-restart 持久）
  - `permanent_session_lifetime = timedelta(days=180)`（半年）
  - `/login` GET 顯示 HTML 表單（內聯，含 🥷 favicon、響應式）
  - `/login` POST 比對密碼 → `session["authed"] = True` → redirect 回 admin 首頁
  - `/logout` 清 cookie
  - `@require_login` 裝飾器套所有 admin route
- API 端未 auth 回 JSON `{ok: false, error: "not_authed"}`，HTML 端 redirect 到 `/login`

這次手機過了。**重新發訊息給老闆**。

---

## 三、IP 白名單（v2 開頭做掉）

老闆能登入後，user 馬上要 IP 鎖：「除了內部區網之外 外部只開 1.34.15.109」（老闆家裡 IP）。

設計分流：
- **公網路徑**：`cwsoft.leaflune.org/admin/cs/*` → Cloudflare 帶 `CF-Connecting-IP` header → Caddy 用 matcher 檢查
- **內部區網**：直接打 `http://192.168.50.6:6005`，**不經 Caddy** → 完全不受 IP 白名單限制（但仍要 login）

Caddyfile：
```caddyfile
handle_path /admin/cs/* {
    @allowed_external {
        header CF-Connecting-IP 1.34.15.109
    }
    handle @allowed_external {
        reverse_proxy 127.0.0.1:6005
    }
    respond 403
}
```

5 個 case 全綠：沒 header 403 / 偽造 1.34.15.109 200 / 偽造其他 IP 403 / 真實公網 CF 改寫成本機 WAN IP 403 / LAN 直連 bypass 200。

**副作用**：本機 curl 公網 URL 現在也會 403（office 的 WAN IP 不在白名單）。要驗證遠端流量得從 1.34.15.109 真實測，或從 LAN 走直連。

---

## 四、手機 RWD 優化

老闆從家裡 1.34.15.109 進來了，截圖回看排版：

- 雙欄塞在窄螢幕，左欄使用者列表「反骨 我是好寶寶」/「手機家族營運總監-嘉…」字被截
- 右欄訊息區被左欄擠壓

user 要求：「**手機或豎屏模式，左邊欄為就只剩名字第一個字的藍圈就好，有消息變成出現在藍圈右上角的紅色氣泡。電腦模式下就照舊不要被影響**」

實作：純 CSS `@media (orientation: portrait)`：

```css
@media (orientation: portrait) {
  .sidebar { width: 64px; }
  .sidebar-header { display: none; }
  .user-item { padding: 12px 0; justify-content: center; position: relative; }
  .user-info { display: none; }
  .badge {
    position: absolute; top: 6px; right: 10px;
    min-width: 18px; height: 18px;
    border-radius: 9px; border: 2px solid #fff;
    /* ... */
  }
}
```

landscape 完全不受影響。

---

## 五、兩個附帶 bug 修

老闆截圖回來時順帶暴露兩個 pre-existing bug：

### 5.1 sidebar 不能滾

`#user-list` 沒設 overflow，超過螢幕高度就被截。簡單 CSS：

```css
.sidebar { overflow: hidden; }  /* 限制範圍 */
.sidebar-header { flex-shrink: 0; }
#user-list { flex: 1; overflow-y: auto; }  /* 自己滾 */
```

### 5.2 「之後的使用者點開沒訊息」

點 5/11 之前的用戶 → 「沒有訊息記錄」，但 badge 顯示有未讀。

抓 root cause：今天上午對 `gtb.py` shadow 模式加了 `image_path` 欄位 + ALTER TABLE migration，但 migration 只在 `init_user_message_table()`（save_shadow_message 才會呼叫）時跑。**5/11 之前不活躍的使用者今天沒新訊息進來 → 沒觸發 migration → 舊表沒 image_path → admin_server.py 的 SELECT 帶 image_path 失敗（try/except 吃掉錯誤）→ 回空 array → 顯示沒訊息**。

修法：admin_server.py 啟動時統一補欄位：

```python
def _migrate_all_message_tables():
    # users 表加 last_viewed_at
    cur.execute("ALTER TABLE users ADD COLUMN last_viewed_at TEXT")
    # 各 messages_* 表補 image_path
    for t in tables:
        try: cur.execute(f"ALTER TABLE {t} ADD COLUMN image_path TEXT")
        except: pass
```

restart 後 log：`scanned 47 message tables, added image_path to 45`（45 個舊表補了；2 個今天活躍用戶今早已被 init migration 補過）。

---

## 六、Badge 邏輯重做：從「沒回覆」改成「沒看過」

舊邏輯：badge = 該使用者 `staff_reply IS NULL` 的訊息數。語意是「沒有工程師發回覆過的訊息」。問題：老闆點進去看過也不會清掉，永遠都亮。

user 要求：「**紅色小圓的數字是甚麼意思 為甚麼我已經點進去看了他還在 我希望他能確實反映有新訊息 最好要有聲音提示 然後我看過之後 紅點數字就消掉**」

設計：每個 user 一個 `last_viewed_at` timestamp：
- DB：`users` 表加 `last_viewed_at TEXT` 欄位（startup migration 處理）
- 後端：
  - `GET /admin/users` 改 unread query：`COUNT(*) FROM messages_xxx WHERE received_at > last_viewed_at`
  - 新 route `POST /admin/view/<user_id>`：把該 user 的 last_viewed_at 設成 now
- 前端：
  - `selectUser()` 點開使用者後 POST 標已讀 → reload users 列表，該 badge 歸零
  - polling 10 秒一次比對 aggregate unread；增加 → 嗶聲

### 6.1 一次性歷史已讀（user 第二次糾正）

第一版實作後，新 column `last_viewed_at` 都是 NULL → unread 算成「全部訊息」→ 載入後 47 個用戶全都亮 badge。

user 反應：「**怎麼還要自己一個個點？**」一開始我想加「全部已讀」按鈕，user 馬上糾正：「**不是要你加一個全已讀按鈕 是目前的歷史訊息就都設已讀 之後的在跳通知**」

直接 SQL：

```sql
UPDATE users SET last_viewed_at = '2026-05-12 14:47:48';
```

順手把 migration 也改成「第一次加欄位時 bulk-set 到 now」，之後 fresh 部署也不會有「初次載入全是紅點」的問題。

---

## 七、提示音

Web Audio API 自製 beep：
- v1：單聲 800Hz 0.4 秒 → user 嫌太短
- v2：**三嗶模式**，每嗶 0.5 秒（指數淡出），中間 0.35 秒停頓，總長 ~2.2 秒

```js
function playBeep() {
  const ctx = new AudioContext()
  for (let i = 0; i < 3; i++) {
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain); gain.connect(ctx.destination)
    const start = ctx.currentTime + i * 0.85
    osc.frequency.value = 800
    gain.gain.setValueAtTime(0.3, start)
    gain.gain.exponentialRampToValueAtTime(0.01, start + 0.5)
    osc.start(start); osc.stop(start + 0.5)
  }
}
```

注意事項：
- 第一次載入到第一次點擊前，browser autoplay policy 會擋 AudioContext，beep 不會響 — 但只要點過任何東西（含登入按鈕）後就 work
- 手機系統靜音模式也會擋

---

## 八、UI 細節：兩個 visual bug

### 8.1 訊息卡 white-space 浪費高度

「AI 草稿」/「已回覆」內文跟標籤之間有大段空白縮排。抓 root cause：CSS `.draft` / `.replied` 設了 `white-space: pre-wrap`，把 **JS template literal 的縮排空白也當文字內容渲染出來**。

修法：把 pre-wrap 從 bubble 移到內層 `<div class="content">`，只作用在實際文字。順手把 padding 從 10px 收到 8px、margin-bottom 從 10px 收到 6px、line-height 從 1.6 收到 1.5。

### 8.2 textarea 不會 auto-grow

老闆「使用草稿」一鍵塞長文（8 點清單 + 多段落）後，textarea 只顯示 ~3 行，被切掉看不到全文。

修法：純 JS auto-grow：

```js
function autoResize(textarea) {
  textarea.style.height = "auto"
  textarea.style.height = textarea.scrollHeight + "px"
}
```

掛在 `input` event（打字時逐字長高 / 縮短）+ 「使用草稿」按鈕 callback（程式設值不會觸發 input event，要手動 call）。CSS 把 `resize: vertical` 改 `none`、加 `overflow: hidden`，純靠 JS 控制高度。

---

## 九、本日成果

### 改動清單

| 檔案 | 改動 |
|---|---|
| `Caddyfile` | 加 `/admin/cs/*` reverse_proxy + IP 白名單 matcher |
| `admin_server.py` | cookie session login、@require_login 套所有 route、startup migration、`POST /admin/view/<user_id>`、`get_users` 改用 last_viewed_at 算 unread |
| `admin/index.html` | 加 `<base href="./">` + 🥷 favicon |
| `admin/app.js` | 改相對 URL、autoResize、playBeep、selectUser 自動標已讀、polling 比對嗶聲 |
| `admin/style.css` | RWD media query、sidebar overflow、`.content` pre-wrap 範圍收窄、bubble padding/margin 收緊 |
| `database/shadow.db` | 一次性 SQL bulk-set 47 個用戶 last_viewed_at |

### Caddyfile snapshot
備份 `docs/Caddyfile-snapshot-pre-admin-auth-2026-05-12.txt` in cwsoft-super-manager（5/8 雙開門備份 pattern 沿用）。

---

## 十、待跟進

### v2 補強（晚一點 / 明天）

- [ ] **mTLS client cert** — 自簽 CA、發 .p12 給老闆裝手機憑證庫。沒裝憑證的裝置即使在白名單 IP 也進不來，這才是老闆說的「鎖憑證」完整版。手機行動網路（4G/5G IP 浮動）只能靠這個解
- [ ] **半年到期換密碼 / 憑證**機制（cron 提醒或自動 rotate）
- [ ] **把同樣 cookie auth 套到 super-manager dashboard (9000)**

### 給 super-manager PROJECT.md 同步

- [ ] cs-admin (6005) 從「對外: 不透過 Caddy（內網管理用）」改成「**對外**: `https://cwsoft.leaflune.org/admin/cs/`（cookie auth + IP 白名單）」
- [ ] 補一段 admin UI auth 架構說明（cookie session、IP 白名單路徑、密碼如何更新）

### 中期

- [ ] 等老闆給家裡 IP 萬一改了再 update Caddyfile 白名單
- [ ] 如果之後要加新管理員（同事），考慮 multi-user login + role

---

## 附：當天關鍵決策推導

### 「為什麼 v1 不直接用 mTLS 一次到位」

deadline 是 4 點。mTLS 要：自簽 CA → 發 .p12 → 教老闆用手機裝憑證庫 → 測試 → 失敗 debug。**老闆裝完才能用**，整個 loop 3-4 小時跑不完。

cookie session 30 分鐘做完、老闆只要記密碼。**保住「4 點前能用」**，mTLS 留 v2 慢慢搞。

### 「為什麼 basic auth 撞到 mobile 才轉 cookie session」

CLI curl 走 HTTP/1.1，401 + WWW-Authenticate 完全正常。沒打到 HTTP/3 路徑。
**老闆手機 Chrome Android** 才走 HTTP/3 + Cloudflare CDN，在這條路徑才暴露 `ERR_HTTP_RESPONSE_CODE_FAILURE`。
教訓：之後 cwsoft.leaflune.org 公網 endpoint 任何 auth / status code 改動，**至少用一個真實手機過一遍**才能簽單。CLI 全綠不等於 mobile 全綠。

### 「為什麼 badge 邏輯重做時第一版只實作 click-mark-read 沒做 bulk-set」

我的腦袋直覺：「last_viewed_at 是新欄位，預設 NULL，第一次打開算全部訊息為 unread 是合理的」— 工程師思維。
user 一句「**怎麼還要自己一個個點？**」直接打破：實務用戶**不會去逐個 click 47 次**，需要 fresh-deploy 就有合理 default。
修正不只是現場 SQL，**也回頭把 migration 邏輯改成「第一次加欄位 → bulk-set 到 now」**，避免下次部署同樣問題。

### 「為什麼 IP 白名單放 Caddy 不放 Flask」

兩個都做得到，但放 Caddy 有兩個好處：
1. **越早擋越好**：non-allowed IP 連 Flask 都不會被叫醒，省 process / DB connection
2. **LAN 直連天然 bypass**：LAN 用戶打 192.168.50.6:6005 跳過 Caddy 整個 layer，不用在 Flask 寫一段「if 來源是 LAN IP 跳過 IP check」邏輯
