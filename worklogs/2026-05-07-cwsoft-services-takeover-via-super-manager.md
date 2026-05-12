# cwsoft 服務全面接管 × super-manager 升級為 Windows Service

- 日期：2026-05-07
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-super-manager、cwsoft-sqlgate、cwsoft-aquan-manager、autoQuotes、general-task-bot、cwsoft-clerk、cwsoft-ai-customer-service、cwsoft-linebot-service、matrix-manager

---

## 一、背景

老闆痛點：「出去跟客戶 demo 服務就掛掉」。原因是 cwsoft 體系 11 個後端服務散落在
VS Code integrated terminal / 手動 cmd / `.bat` 啟動，VS Code 一更新或不小心關掉
全部陪葬。4/27 會議建立了 cwsoft-super-manager，但只完成框架、沒實際接管，11 個
服務仍是「super-manager spawn 表面 OK 但實際是 VS Code terminal 在做事」的假陽性
狀態。

5/7 目標：把所有服務從 VS Code terminal **真實**接管到 super-manager，並把
super-manager 自己升級成 Windows Service，徹底脫離 IDE / SSH session 依附。

---

## 二、接管 SOP 的成形

每個服務接管時都會踩到三類雷（後來補了 D 類）：

| 類別 | 內容 |
|------|------|
| **A. 服務本體** | `debug=True` 改 `False`、host/port 對齊 services.json、`.env` 確認 |
| **B. services.json** | `health_path` 對到真實端點、`health_type` 選對、cmd/cwd/port 對齊 |
| **C. 周邊衛生** | repo 上 git + .gitignore、過時文件對齊、舊啟動方式淘汰 |
| **D. 健檢假陽性**（5/7 新增） | health endpoint 不存在被當健康（404 < 500）、舊 process 騙過 health、phantom socket |

完整 SOP 寫進 [cwsoft-super-manager/PROJECT.md](https://github.com/colombo0718/cwsoft-super-manager) 「接管 SOP」章節。

---

## 三、接管實戰時間軸

### 5/7 早上：OTP/bind 接管（兩個小服務當示範）

- cwsoft-sqlgate 整個 repo 之前**沒上 git** → init + .gitignore（排除 .env、*.db、
  caddy.exe）→ commit + push 上 GitHub private
- 移除過時 Caddyfile（主控在 `C:\Program Files\cloudflared\Caddyfile`）
- 一次性測試腳本 `send_test_sms.py` / `tryAddBranch.py` 移到 `scratch/`
- README.md / PROJECT.md 的 port 寫錯 (bind=6000、OTP=5000) 修正為實際 (4002 / 4001)
- OTP_server.py / bind_server.py `debug=True` → `False`
- services.json 的 OTP/bind `health_path: "/ping"` → `"/health"`（兩個服務只有
  `/health` 沒有 `/ping`）
- 演練成功，2 個服務真實接管

### 5/7 中午：剩餘 9 個服務全接管 + super-manager 上 nssm

#### 階段 1：services.json 修正 + 大屠殺

- `aquan-manager (6000)` 改 `gtb_dev.py + --conf pos_dev` → `gtb.py + --conf pos`
  - 老闆實際在用的是最舊的 `main.py pos`（monolithic 時代）
  - super-manager 之前 spawn 的「假阿全」是 dev 引擎 + dev conf
  - 切到正式版散裝引擎才是真實接管
- 殺 super-manager + 11 個服務 child + VS Code 殘留共 37 個 process
- 重啟 super-manager → 11/11 顯示 running

#### 階段 2：accounting (5000) 內部接救

- 發現 5000 仍被一個 phantom socket 佔住：
  - PID 144648 （`Stop-Process` 報「找不到 PID」但 netstat 顯示在 LISTEN）
  - 真正持有者是它的活 child PID 329236（`pdfServer.py` orphan，從某次
    Claude session bash spawn 留下）
- 殺 child → kernel 自然釋放 socket → super-manager restart accounting → 真接管

#### 階段 3：dashboard 改進

- 加 favicon 🎛️
- `app.config["TEMPLATES_AUTO_RELOAD"] = True` — 之後改 dashboard.html 免重啟

#### 階段 4：super-manager 升級為 Windows Service

- 寫 `setup-nssm.cmd` 一鍵把 super-manager 註冊成 Windows Service
- 機器上已有 nssm（line_binding_server.py 已用它跑成 service）
- 第一次 nssm start：`SERVICE_PAUSED` → log: `ModuleNotFoundError: No module named 'flask'`
- 摸索出 5 個必設環境變數（見下節）
- 11/11 全綠 + super-manager 完全脫離 SSH session

---

## 四、摸索出的關鍵 knowhow

### nssm 跑 Python service 的 5 個環境變數

獨立寫成 [docs/nssm-python-service.md](https://github.com/colombo0718/cwsoft-super-manager/blob/main/docs/nssm-python-service.md)，重點：

| 變數 | 解的問題 | 真實事故 |
|------|----------|----------|
| `PYTHONPATH` | LocalSystem 看不到 user site-packages | `ModuleNotFoundError: No module named 'flask'` |
| `APPDATA` | `site.getuserbase()` 在 service context 算錯 | 不直接致命，但 pip / setuptools 等會走偏 |
| `USERPROFILE` / `HOME` | `~/.app/config` 解析錯誤 | cloudflared 找不到 `~/.cloudflared/cert.pem` |
| `PATH`（絕對路徑） | nssm 不展開 `%PATH%` | super-manager 起得來但 spawn child 找不到 `py` |
| `AppDirectory`（不是 env） | service 預設 cwd 是 System32 | 任何用相對 path 開檔的都會炸 |

### Windows phantom socket 現象

process 死了但 LISTEN socket 沒釋放，OS 還掛它名字。`Stop-Process` 報「找不到 PID」
但 netstat 持續顯示。通常是某個活著的 child 還持有從 dead parent 繼承的 socket
handle — 找出真正的 child kill 掉，OS 自然釋放。

### Health check 假陽性的兩種模式

1. **404 lucky pass**：`manager.py` 看 `status_code < 500` 視為健康，但 404 也 < 500，
   服務根本沒對應 endpoint 也被當健康。
2. **舊 process 騙過 health**：super-manager spawn 新 instance 撞 port 失敗，但舊
   process 還活著回應 health endpoint，super-manager 看 port 通就回綠。

驗證真接管的方法：用 `Get-NetTCPConnection -LocalPort N` 找 OwningProcess，trace
parent chain 確認真的是 super-manager 的子孫。

### GTB 系列 chatbot 三版本入口

- `main.py pos` — 舊 monolithic（淘汰，但被 cwsoft-linebot-service 的 VS Code
  task「一鍵啟動」綁著復活）
- `gtb_dev.py --conf <name>_dev` — 散裝開發版
- `gtb.py --conf <name>` — 散裝正式版

PowerShell 環境變數 `$GTB` / `$GTB_DEV` 指向後兩者，但 PowerShell-only（nssm
看不到、cmd / SSH 看不到，services.json 要寫死絕對 path）。

### cwsoft-aquan-manager 的「散裝模式」結構

```
cwsoft-aquan-manager/
├── config/
│   ├── mission_pos.json       ← 正式版 mission（--conf pos）
│   ├── mission_pos_dev.json   ← 開發版
│   ├── prompts_pos.ini
│   └── prompts_pos_dev.ini
├── database/
│   ├── config.db
│   ├── conv_U38daae74...db    ← 老闆對話歷史（L2 隱私）
│   ├── feedback_loop.db
│   └── todo_list.db
├── oa_registry.json           ← LINE Channel Secret + Access Token（L2 高機密）
└── customerlist.txt
```

「散裝模式」= 從 monolithic GTB 拆出，每個 chatbot 獨立 repo + 自己的
config/database/oa_registry，共用同一支 GTB 引擎。

---

## 五、達成狀態

```
Windows OS (boot 自啟)
  └─ Windows Service: cwsoft-super-manager (nssm)
       └─ super-manager (Python Flask :9000)
            ├─ caddy           ✅
            ├─ cloudflared     ✅
            ├─ accounting      ✅ ← 老闆儀表板
            ├─ sqlgate         ✅
            ├─ otp-server      ✅
            ├─ bind-server     ✅
            ├─ clerk           ✅
            ├─ kbcs            ✅
            ├─ cs-admin        ✅
            ├─ aquan-manager   ✅ ← 阿全 (gtb.py + pos)
            └─ cs-shadow       ✅
```

11/11 全綠、重啟次數 0。VS Code 怎麼開關 / SSH 怎麼斷 → 服務完全不受影響。
重開機 super-manager 自啟，老闆 demo 不會再因為 IDE 操作而掛掉。

---

## 六、本輪新增 / 更新文件

**cwsoft-sqlgate**（已上 GitHub private）
- `.gitignore`、`README.md`、`PROJECT.md` 對齊 + 文件 port 修正
- `OTP_server.py` / `bind_server.py` `debug=False`
- `scratch/` 整理一次性測試腳本

**cwsoft-super-manager**（4 個本地 commit，待 push 上 GitHub）
- `services.json` — OTP/bind health_path /ping → /health、aquan-manager 改 gtb.py + pos
- `templates/dashboard.html` — favicon 🎛️
- `app.py` — TEMPLATES_AUTO_RELOAD
- `setup-nssm.cmd` — 一鍵 Windows Service 化（含 5 個環境變數 fix）
- `docs/nssm-python-service.md` — nssm 環境變數踩坑完整指南
- `PROJECT.md` — 接管 SOP + 5/7 兩階段接管紀錄
- `TODO.md` — 規劃未來事項（L3 variant 切換、接管收尾、SOP 改進、文件整理等）
- `CLAUDE.md` — 通用工作規範

---

## 七、待跟進

### 接管收尾（衛生補完）
- [ ] cwsoft-super-manager 上 GitHub（5 個本地 commit 待 push）
- [ ] cwsoft-aquan-manager 上 git + .gitignore（含 LINE token + 對話歷史保命）
- [ ] autoQuotes 上 git + .gitignore（319 個未 commit 大概率含客戶資料）
- [ ] digital-agent-xiaohao 上 git
- [ ] 拆除 cwsoft-linebot-service 舊 workspace（避免誤點召喚舊時代）
- [ ] 釐清 line_binding_server (5001 第二個 listener) 是什麼

### 服務本體改進
- [ ] autoQuotes/accountSystemServer.py `debug=True → False`
- [ ] gtb.py + accountSystemServer.py 加真正的 `/health` endpoint
- [ ] sqlgate 主服務的安全/穩定性（autocommit、SQL injection、缺 attach_customer）

### super-manager 本體改進
- [ ] L3：variant 切換 + 一鍵 demo mode（dev↔prod）— 老闆 demo 痛點根治
- [ ] `/api/projects` endpoint（4/27 會議遺留，跨專案進度概覽）
- [ ] dashboard 加事件流（重啟歷史、失敗紀錄）
- [ ] services.json per-service `env` 欄位支援

### MM 端
- [ ] 更新 INDEX.md 把這次會議掛到相關專案下

---

## 附：當天的關鍵決策推導

### 「先接管 OTP/bind 當示範」 vs 「一次接 5 個」

**選擇前者**。理由：
- OTP/bind 是 sqlgate 體系的小弟，failure blast radius 最小
- 走完一次完整 SOP 把雷踩出來，建立通用模板
- 後面接 9 個就有 SOP 跟著走，不會每個重新摸索

實際結果：OTP/bind 接管摸出 A 類（debug）+ B 類（health_path）的雷，後面 9 個都
受惠。

### 「漸進切換」 vs 「全清重啟」

**選擇後者**。理由：
- 老闆當下沒在用（早上 vs 中午）
- 漸進切換每段都要等 super-manager monitor_loop 一輪、累計斷線時間更長
- 全清重啟可以一次解掉所有「假陽性」狀態，dashboard 從此可信

實際結果：30-60 秒全斷，老闆無感，從此 dashboard 真實反映系統狀態。

### 「super-manager 跑 user 帳號 + 密碼」 vs 「LocalSystem + 環境變數注入」

**選擇後者**。理由：
- 不需要儲存 user password 在 service config
- user 改密碼不會壞 service
- 環境變數是 declarative 的設定，未來看得懂

代價：需要摸索 5 個環境變數（PATH/APPDATA/PYTHONPATH/USERPROFILE/HOME）— 這個
痛苦變成 [docs/nssm-python-service.md](https://github.com/colombo0718/cwsoft-super-manager/blob/main/docs/nssm-python-service.md)
的素材，未來任何 Python service 包 nssm 都受惠。
