# CWSoft 戰略藍圖萃取與保存

- 日期：2026-05-10（接續 5/7-5/8 兩天 cwsoft-super-manager 接管 + RUNTIME.md 體系 + 雙開門上線之後）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-meeting-tracker、cwsoft-super-manager、matrix-manager

> 5/7-5/8 兩天聚焦在「**技術層**」（接管 11 服務、nssm 化、RUNTIME.md 體系、雙開門 Apache patch、粽子頭架構釐清）。
> 今天聚焦在「**戰略層**」 — 把老闆的 AI 服務遠景藍圖萃取成 super-manager 的權威文件。

---

## 一、觸發點：純粹從一個 git pull 開始

user 請我幫 cwsoft-meeting-tracker 跑 git pull。拉到 +9133 行新內容：4 份新會議紀錄
（2025-06-30 / 2026-04-27 / 2026-04-30 / 2026-05-05）+ 5 份雅婷逐字稿 + 3 份 projects 進度檔
更新。

順帶意外發現：**SSH session 對 git pull 是通的**（不像 push 卡 wincredman），
表示之後跨 repo 拉資料 Claude 自己能做，不需要 user RDP。

user 看完報告後追問：「你把關於 cwsoft 所有的會議紀錄都看一下，了解一下老闆對於整個
AI 服務遠景藍圖是甚麼」。從技術運維轉向戰略理解。

---

## 二、為什麼委派 agent 而不是自己讀

範圍盤點：
- **20 份**會議紀錄（2025-06 到 2026-05，跨 11 個月）
- **13 份**專案狀態檔（projects/）
- **1 份**商談紀錄（business/）
- 加上 customerlist.txt / PROJECT.md / 校正對照表

預估 30k+ token raw 內容。如果 main Claude 自己讀，會吃光 context，後續對話品質下降。

決策：**委派 general-purpose agent 一次到位**。
- agent 自帶獨立 context，不污染 main
- 寫詳細 prompt 限制範圍 + 輸出格式（1500-2500 字）
- 要求區分「老闆親口」vs「跨會議推論」vs「不確定」三層
- 要求附引用來源（會議日期 + projects 檔名）

agent 跑 ~7 分鐘，產出 2300 字結構化 markdown，引用密集到具體會議日期。

---

## 三、戰略藍圖核心發現

完整內容已存 [`cwsoft-super-manager/docs/cwsoft-vision.md`](https://github.com/colombo0718/cwsoft-super-manager/blob/master/docs/cwsoft-vision.md)，本檔只摘關鍵 insight：

### 老闆的 north star（親口語錄）

- 「程式碼不值錢，客戶才是核心資產」（2026-03-30）
- 「軟體公司要拼速度，快打慢」、「人下目標、AI 24 小時持續迭代、人驗收」
- 「東西要做得有趣，自然會帶錢來」（2025-06-30）
- 「未來『用講的時代』」（2026-04-30 — 老闆甚至想買翻蓋手機貼車上）
- 「客戶要的不是新功能，是客人」

濃縮一句：**「用 AI 把 cwsoft 從『客製軟體商』轉型為『客戶經營平台』」**。

### 服務體系藍圖（按用戶分類）

- **A. 老闆自用** — 阿全（小幫手）/ Codex 開發協作 / Claude Code 巡檢
- **B. 對 cwsoft 客戶（B2B 門市）** — 小葳 AI 客服 / 進階行銷系統 / 維修加盟管理 / AI 助理（POS 語音版，未開放）
- **C. 對最終消費者（C 端）** — LIFF 主選單 / iPhone 預購 / 集點優惠券 / 維修進度通知

### 商業意圖四層

1. 訂閱差異化（進階行銷 3000+1000、要買就全買、收頭不收尾）
2. 加值與綁約（維修平板送年約）
3. 降低人力成本（小葳 10% → 爆炸式成長）
4. 歷史包袱整合（維護合約管理整合月收估 300 萬）

### 跨服務整合趨勢

老闆**確實想串成一個 AI 大腦**：
- 「共用核心 + 設定檔分流」（2026-04-10 親口）
- 「MD 文件 + CLI 降 token」（2026-04-30）
- 「CWSoft 整合 vs Ocard 兩套」（2026-04-27 — 「整合是優勢、是賣點」）

---

## 四、決策：為什麼存 super-manager 而非 cwsoft-meeting-tracker

兩個合適的歸宿都評估過：

| 選項 | 優 | 劣 |
|---|---|---|
| `cwsoft-meeting-tracker/vision-synthesis-2026-05.md` | 跟 meetings/ projects/ 同 repo，跨會議綜合屬於這 repo 的職能 | meeting-tracker 是「整理工具」repo，戰略藍圖讀者主要不是用這個 repo 的人 |
| `cwsoft-super-manager/docs/cwsoft-vision.md` | super-manager 是「中央指揮中心」，**戰略層應該跟戰術層擺一起**；其他 Claude 進來看 PROJECT.md 自然能找到 | 跟資料源（meetings/）分開了 |

**user 選後者**：「這份戰略藍圖很重要，保存在你這吧」。理由更深 —
super-manager 是 Claude 主要工作的地方，戰略層在這裡 = Claude 一進來就有 context，
做技術決策時自然會對齊老闆方向。

---

## 五、戰略 vs 戰術文件層次

加完 vision.md 後，super-manager docs 的層次清晰：

```
PROJECT.md（戰術層 — 服務怎麼跑、誰是誰）
   └─ docs/cwsoft-vision.md（戰略層 — 為什麼跑、要往哪去）         ← 5/10 新加
   └─ docs/leaflune-to-office-migration.md（執行層 — 怎麼遷）
   └─ docs/nssm-python-service.md（技術層 — 怎麼設環境）
   └─ docs/runtime-contract-template.md（協作層 — 跨 repo 怎麼聲明執行契約）
```

**PROJECT.md 開頭加 reference link**：未來其他 Claude 進來看 PROJECT.md 第一段就會
看到「戰略層藍圖在 docs/cwsoft-vision.md」，技術決策時對齊公司方向變成 default 行為。

---

## 六、與 super-manager 5/7-5/8 工作的契合度驗證

vision.md §7 寫了一段「跟 super-manager 工作的契合點」 — 把老闆藍圖跟過去兩天技術
工作對照，驗證**沒有偏離方向**：

| 老闆藍圖（親口）| super-manager 對應 |
|---|---|
| 「共用核心 + 設定檔分流」（2026-04-10）| 散裝 GTB 模式：aquan-manager / cs-shadow / xiaohao 共用 gtb.py 引擎，各自 mission_*.json |
| 「MD 文件 + CLI 降 token」（2026-04-30）| 5/8 建立的 RUNTIME.md 跨 repo 協作機制 |
| 「先內部跑穩再對客戶開放」 | super-manager 接管 + nssm 化讓「老闆 demo 不掛」是基本盤 |

**完全契合**。也就是說 5/7-5/8 兩天接管 + nssm + 雙開門 + 文件體系建立，全部都在
老闆藍圖往前推進，不是技術人自己玩。

vision.md 也指出 6/1 零壹進階行銷上線是個 milestone — **6/1 上線前該排上**：
- LIFF 前端遷 office
- 阿全 mission_pos.json 內部呼叫改 127.0.0.1
- 進階行銷的核心鏈（LIFF + LINE OA + sqlgate）必須穩

這些是 vision 給 super-manager TODO 的優先序提示。

---

## 七、Living document 設計

vision.md 不是「一次寫死」的文件。內容 §9「維護備忘」明確寫了未來怎麼更新：

- **每月一次**輪值更新（讓 Claude 跑一次跨新會議的綜合）
- **重大決策後**立即更新（放棄某產品、新拿到大客戶、商業模式改變）
- **6/1 零壹進階行銷上線後**重要 update（會有第一個收費客戶 feedback）

更新流程：
1. `git pull` cwsoft-meeting-tracker 拉最新會議紀錄
2. 委派 Claude general-purpose agent 跨 repo 重新萃取（prompt 範本見產生紀錄）
3. 跟舊版 diff，把新增的部分整合進來
4. 「最後更新」改日期，「不確定」清單更新（落地的有些已成 hard fact、新疑點冒出）

---

## 八、本日成果

### cwsoft-super-manager
- 新檔：`docs/cwsoft-vision.md`（210 行戰略藍圖）
- 更新：`PROJECT.md` 開頭加 vision link

### matrix-manager
- 本檔 `meetings/2026-05-10-cwsoft-vision-synthesis-and-archival.md`
- INDEX.md 同步更新

### cwsoft-meeting-tracker
- `git pull` 拉到 5 份新會議紀錄 + 5 份新逐字稿（+9133 行）

---

## 九、待跟進

### 立即（給未來其他 Claude）

- [ ] 進 super-manager 工作時，**先看 docs/cwsoft-vision.md 戰略層**，再看 PROJECT.md 戰術層 — 技術決策對齊老闆方向

### 短期（6/1 前）

- [ ] **LIFF 前端遷 office**（vision §7 提到的 milestone 配套）
- [ ] **阿全 mission_pos.json 內部呼叫改 127.0.0.1**（同上）
- [ ] 6/1 零壹進階行銷上線後，**馬上跑一次 vision 更新**（會有第一個收費客戶 feedback 進來）

### 中期

- [ ] 每月一次 vision 維護輪值（6/10 前後第一次正式更新）
- [ ] 觀察「老闆親口 vs 推論」的「不確定」清單，看哪些落地了、哪些被推翻

### 長期

- [ ] vision 更新累積一年後檢視「準度」 — 我寫的「推論」有多少被會議 confirm、多少被 falsify？這個 retrospective 對未來 vision synthesis 是個校準

---

## 附：當天的關鍵決策推導

### 「為什麼委派 agent 而不是自己讀 20 場會議」

main context 是稀缺資源。20 場會議 raw content 30k+ token，讀完後續對話品質下降。
委派 agent 等於「把研究外包給獨立 thread」，main context 保持乾淨。

agent 設計重點：明確輸出格式（1500-2500 字結構化 markdown）+ 三層 epistemic
labeling（親口 / 推論 / 不確定）+ 引用來源。寫好 prompt 比 main 自己讀效率高 5-10 倍。

### 「為什麼分『戰略層』vs『戰術層』vs『執行層』」

reader 不同：
- 戰略層 → 接手者 / 業務決策者 / Claude 第一次工作前先看
- 戰術層（PROJECT.md）→ 開發者 / Claude 改技術細節時看
- 執行層（migration / nssm / template）→ 動工時看

把這三層合在一份檔案裡，每個 reader 都得 scan 整份找自己要的。**分檔讓查找更精準**。

### 「為什麼存 super-manager 不存 meeting-tracker」

meeting-tracker 是「raw materials repo」（會議紀錄、逐字稿、專案狀態）。
super-manager 是「synthesis 與 action repo」（戰略藍圖、技術設計、運維工具）。

藍圖是 synthesis 結果，存 synthesis repo 比存 raw 旁邊更對。也讓 Claude 自然在
super-manager 工作時被 vision 觸及。

### 「為什麼 vision 要明確標『不確定』」

intellectual honesty。把推論誤當 hard fact 是最危險的事 — 後人引用「老闆說 X」
時，要能追溯到「真的說過嗎」。標籤 `不確定（？）` 讓未來 Claude 知道哪些待 confirm，
而不是繼承一個錯誤的「事實」。
