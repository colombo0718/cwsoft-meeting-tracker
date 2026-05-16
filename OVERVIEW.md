# OVERVIEW.md — CWSoft 公司現況儀表板

> 「進公司第一天，AI 帶你看的那張圖」。
>
> - 客戶專案明細：`README.md` PROJECT_STATUS / `projects/`
> - 詳細討論過程：`meetings/`（人對人）、`worklogs/`（人對 AI）
> - 戰略長期願景：[cwsoft-super-manager/docs/cwsoft-vision.md](../cwsoft-super-manager/docs/cwsoft-vision.md)
> - 下半年具體走法：[cwsoft-super-manager/docs/cwsoft-h2-2026-direction.md](../cwsoft-super-manager/docs/cwsoft-h2-2026-direction.md)
>
> 最後更新：2026-05-12

---

## 一、一句話定位

> **「用 AI 把 cwsoft 從『客製軟體商』轉型為『客戶經營平台』」**

上半年（2026 H1）把技術底盤鋪好（11 個服務常駐 + 監控中央化）。為
下半年（2026 H2）兩件事：
1. **把客戶從客服請走** — AI 自動回覆比例：年底 10%、2027 年 50-80%
2. **把系統從工程師詞彙翻成老闆詞彙** — 命名整頓、架構圖、週報格式都改成老闆能讀懂

---

## 二、服務體系（按誰受益分類）

### A. 老闆自用
| 服務 | 做什麼 | 狀態 |
|---|---|---|
| 阿全（全葳小助手）| 老闆每天用的 LINE bot — 出報價單、查點數、跨服務調度 | ✅ 上線 |
| Codex 開發協作 | 寫程式 + 程式碼直接回問題 | ✅ 羿宏在用 |
| Claude Code 巡檢 | 服務監控 / 文件整理 / 戰略文件維護 | ✅ 士豪在用 |

### B. 對 cwsoft 客戶（B2B 門市）
| 服務 | 做什麼 | 狀態 |
|---|---|---|
| 小葳 AI 客服 | 客戶問題 AI 直接回 → 影子模式測試中 | 🟡 影子驗證中 |
| 進階行銷系統 | 零壹通訊行訂的，月租化包套 | 🟡 6/1 正式上線 |
| 維修加盟管理 | 老客戶月租化的施力點 | ⏳ 規劃中 |
| POS 內建 AI 助理（語音版）| 老闆用的，員工版下半年才開放 | ⏳ 未開放 |

### C. 對最終消費者（C 端）
| 服務 | 做什麼 | 狀態 |
|---|---|---|
| LIFF 主選單 | 客戶在 LINE 內的入口 | ✅ 上線 |
| iPhone 預購 | 限時搶購功能 | 🟡 開發中 |
| 集點優惠券 | 零壹的會員回饋系統 | 🟡 6/1 隨進階行銷上線 |
| 維修進度通知 | 維修進度自動推播 | ⏳ 規劃中 |

### F. 已下架 / 待清理
- `cwsoft-clerk`（書記排程 API）— 2026-05-12 下架，從未真實接入
- `cwsoft-linebot-service`、`cwsoft-bot-boot.bat` — 舊時代化石

---

## 三、資訊部當下三大主軸（H2 2026）

### 主軸一：客服自動化 KPI
| 時點 | 目標 | 內容 |
|---|---|---|
| 2026 年底 | **10%** | 基本問題 AI 直接回（怎麼安裝、帳號密碼）|
| 2027 年 | **50-80%** | 進階問題、跨表查詢 |

**信心度 gating**：≥95-98% 自動回、低於門檻走影子模式給人工確認。多重 AI 投票判信心度。

### 主軸二：GTP × Codex 並行整合
```
使用者訊息 → GTP（路由 + 抓對應知識章節）
            → Codex / LLM（基於 context 回答）
            → Codex / Claude CLI（審核回覆對不對）
            → 回覆使用者
```
- **GTP**（士豪）= 任務型，拆語意、抓 MD 章節
- **Codex**（羿宏）= 程式碼層直答，但接介面層不行
- **整合是賣點** — 跟 Ocard 兩套對打的差異化

### 主軸三：命名 + 架構圖整頓
| 舊名（工程詞）| 新名（老闆詞）|
|---|---|
| 開後門 / gtb_dev /sim | **Multi-source / Manager** |
| GTP（General Task Bot）| **知識庫回應系統** |
| OP + 會員綁定 | **智慧門市會員** |

設計交付物：11 個服務的**樹狀架構圖**（老闆看得懂的那種）。

---

## 四、近期里程碑時間軸

| 日期 | 事件 | 影響 |
|---|---|---|
| ~~5/9~~ | ~~羿宏出國~~ | 已過；Codex 線暫緩 |
| 5/16 | 羿宏返國 | Codex 線恢復進度 |
| **6/1** | **零壹通訊行進階行銷正式上線** | 第一個收費客戶 feedback 進來 — 同時也是 6 個月內最關鍵 release |
| **6 月初** | **士豪論文口試** | 之前進度需求降低；口試後恢復全速 |
| **6 月中起** | 影子模式 WebView app、Codex 串接 | 論文後動工 |
| **年底** | 客服自動化達 10% | KPI 第一道驗收 |
| **2027** | 自動化達 50-80% | KPI 終局 |

---

## 五、客戶專案儀表板

完整看板在 [`README.md`](README.md) PROJECT_STATUS 段落，13 個專案最新狀態自動更新。

**最熱專案前 3**（按 6/1 上線壓力）：
1. **零壹通訊行 — 集點系統** — 6/1 完整上線
2. **小幫手 / 阿全** — 雙層 LLM、語音勘誤、12+3 帳單補強
3. **小葳 AI 客服** — 影子模式整合、權限分流、知識庫回寫

---

## 六、人員 + AI 同事當下分工

### 人員
| 角色 | 主責 |
|---|---|
| **彥偉** | 老闆，vision setter、業務決策、客戶對接 |
| **士豪** | GTP 線（任務型 chatbot 引擎、客服自動化、super-manager） |
| **羿宏** | Codex 線（程式碼層直答、POS 內建客服、會員資料） |

### AI 同事
| Agent | 用途 |
|---|---|
| **Claude Code** | 服務監控、文件整理、戰略文件、worklog 寫作 |
| **Codex CLI** | 寫程式、code review、知識庫回答 |
| **Cursor** | 互動式 IDE 開發 |

### 跨人協作原則
- **士豪 ↔ 羿宏**：用 AI 對 AI 互查 — 偵測重複工作、抽共用 component（認證模塊不要各做一份）

---

## 七、技術底盤簡要

> 詳細服務清單 / 啟動 / 監控規格在 [cwsoft-super-manager/PROJECT.md](../cwsoft-super-manager/PROJECT.md)。本節只給「公司全景」。

- **11 個常駐服務** 由 super-manager 統一管理（spawn / health check / auto-restart）
- **三層架構**：
  - Apache 2.4 (`office.cwsoft.com.tw`) — 公司範式，同事既有服務
  - Caddy + cloudflared (`cwsoft.leaflune.org`) — 士豪這條探索線，新服務都掛這
  - super-manager (port 9000) — 全部後端服務的總管
- **dashboard**：`http://localhost:9000/`（內部存取）
- **兩通道過渡**：長期目標把 leaflune 流量遷到 office，但 fragile 動作不急

---

## 八、業務面備忘

- **維護合約月租化** — 300 萬目標 vs 150 萬實際；舊客戶月租化要靠新功能升級才有施力點
- **新功能優先** — AI 普及使基礎軟體售價下降，新功能要盡早出去推
- **新威會員 12 點訊息**（5/12 待辦）— 不要漏

---

## 九、維護備忘

### 更新節奏
- **每月一次**輪值更新（讓 Claude 跑一次跨新會議/worklog 的綜合）
- **里程碑前後**立即更新（6/1 上線、6 月口試結束、客戶試用回饋進來）
- **戰略決策後**：vision.md 改了 → OVERVIEW 對齊

### 更新流程
1. 讀 `meetings/` / `worklogs/` 最近一個月新增
2. 對照 super-manager 端的 `cwsoft-vision.md` / `cwsoft-h2-2026-direction.md` 看戰略有沒有變
3. 更新本檔的「狀態」欄、時間軸、人員分工
4. 「最後更新」改日期

### 與其他文件的關係
| 文件 | 範圍 | 對誰 |
|---|---|---|
| `cwsoft-vision.md`（super-manager）| 1-3 年戰略 north star | Claude 工作前 context |
| `cwsoft-h2-2026-direction.md`（super-manager）| 6 個月具體走法 | Claude + 老闆 |
| **本檔 `OVERVIEW.md`** | **公司當下儀表板** | **老闆 / 同事 / 新進 AI** |
| `README.md` PROJECT_STATUS | 客戶專案進度快照 | 老闆 / 客戶對接 |
| `projects/*.md` | 單一專案明細 | 開發者 / 對應客戶 |
| `meetings/` `worklogs/` | 過程 raw materials | 追溯歷史 |
