# PROJECT.md — cwsoft-project-tracker

## 這個專案是什麼

CWSoft 公司的**工作紀錄與專案追蹤中心**——兩種內容並存：

1. **人對人會議紀錄**：整理同事 / 客戶會議逐字稿，產出標準會議紀錄與專案狀態檔
2. **人對 AI 工作紀錄**：cwsoft 同仁與各種 agent（Claude / Codex / Cursor / ...）協作推進工作的紀錄

兩者皆供老闆透過 AI 查閱資訊部門工作進度。

---

## 治理層定位（給 AI 讀）

本 repo 是 **MM 管轄的次級治理工具**：

```
colombo 心中的治理結構：

  matrix-manager (MM)           ← colombo 的最高治理層
       │
       ├── LL 宇宙專案群        ← 個人創業
       ├── 論文 / 教學
       └── cwsoft-project-tracker  ← 本 repo（次級治理工具，CWSoft 範圍）
              │
              ├── meetings/   人對人會議
              ├── worklogs/   人對 AI 工作紀錄
              └── projects/   11 個子專案狀態檔
```

- **對 colombo 視角**：MM 之下的次級治理層
- **對老闆 / 同事視角**：CWSoft 公司工作的最高記錄中心
- **性質**：跟 MM 同類（都是「專案管理工具」），但範圍只限 CWSoft

### 邊界（AI 進來時的行為準則）

```
✓ 允許：在本 repo 內讀寫、推進 CWSoft 相關工作
✓ 允許：worklogs/ 寫 cwsoft 同仁 × 各種 agent 的工作紀錄
✓ 允許：透過 SOP（CLAUDE.md）整理會議與更新 projects/
✓ 允許：跟老闆 / 同事透過 AI 查閱對話

✗ 不要：讀寫 LL 宇宙的內容（leaflune / II / RR / DD / XX 等）
✗ 不要：跨界引用個人創業相關資訊（避免商業/隱私洩漏）
✗ 不要：把 matrix-manager 內部結構暴露給對外讀者
```

老闆 / 同事用 AI 查本 repo 時、AI 只看本 repo 範圍即可。

---

## 架構概覽

```
cwsoft-project-tracker/
├── minutes/                    ← 原始逐字稿（雅婷提供，.txt）
├── meetings/                   ← 整理後會議紀錄（.md）——人對人
├── worklogs/                   ← 人對 AI 工作紀錄（.md）——cwsoft 同仁 × 各種 agent
├── projects/                   ← 各專案狀態檔（每專案一份 .md）
├── business/                   ← 業務相關文件
├── 語者、客戶、專案名稱校正.md  ← 語者辨識規則、名稱對照
├── 會議記錄整理模板.md          ← meetings/ 輸出格式規範
└── customerlist.txt            ← 客戶正式名稱列表
```

> `meetings/` 與 `worklogs/` 的差異與規範詳見 [`worklogs/README.md`](worklogs/README.md)。

---

## SOP：處理一份新逐字稿

### Step 1 — 讀取逐字稿
- 讀取 `minutes/` 中未處理的 .txt 檔案
- 同一天有多份逐字稿，合併為同一份會議紀錄
- 日期從檔名推斷，格式統一為 YYYY-MM-DD

### Step 2 — 整理成會議紀錄（初稿）
- 依照 `會議記錄整理模板.md` 的格式輸出
- 此階段語者**保留原始標記**（語者1、語者2、語者3），不做推測
- 客戶名稱保留逐字稿中的說法，加上 `【待校正】` 標記
- 存為 `meetings/會議記錄_YYYY-MM-DD.md`

### Step 3 — 內容校正
- 依照 `語者、客戶、專案名稱校正.md` 的規則進行校正：
  1. **語者辨識**：根據每段發言的內容與職責，將語者1/2/3 替換為真實姓名（彥偉、羿宏、士豪）
  2. **客戶名稱**：對照 `customerlist.txt`，修正誤識的客戶名稱，移除 `【待校正】` 標記
  3. **專案名稱**：套用專案名稱對照表，統一用詞
- 無法確認的項目保留 `【待確認】` 標記，不要亂猜

### Step 4 — 更新專案狀態檔
- 從會議紀錄的「待辦」與「決議」中，依專案分類任務
- 若 `projects/{專案名稱}.md` 已存在，追加或更新任務
- 若不存在，建立新檔案，格式：

```markdown
# 專案：{專案名稱}

## 當前狀態
> {一句話描述目前進度}

## 任務追蹤
| 任務 | 負責人 | 期限 | 狀態 |
|------|--------|------|------|
| {任務} | {人名} | {日期} | 進行中 / 待處理 / 完成 |

## 會議記錄索引
- [YYYY-MM-DD 會議](../meetings/會議記錄_YYYY-MM-DD.md)
```

### Step 5 — 更新 README.md 看板
- 讀取所有 `projects/*.md`
- 更新 README.md 中 `<!-- PROJECT_STATUS_START -->` 至 `<!-- PROJECT_STATUS_END -->` 之間的內容
- 格式：

```markdown
| 專案 | 當前狀態 | 最近更新 |
|------|----------|----------|
| [專案名稱](projects/專案名稱.md) | {一句話狀態} | YYYY-MM-DD |
```

---

## SOP：寫 worklog（人對 AI 工作紀錄）

worklog 是 cwsoft 同仁跟各種 agent 的工作協作紀錄，存於 `worklogs/`。
**寫作規範詳見 [`CONVENTIONS.md`](CONVENTIONS.md)**——含：
- 何時寫 worklog（Trigger：對話超過 30 則 / 完成架構決策 / 有實質改檔 等）
- 檔案命名（`YYYY-MM-DD-主題.md`，kebab-case）
- Header 四欄位必填（日期 / 主機 / 參與者 / 相關專案）
- 必要段落（討論摘要 / 本輪新增更新檔案 / 待跟進）
- 整理原則（決策明確 / 守邊界）

AI 看到 Trigger 條件成立時，**主動提醒 colombo**：
「這段討論建議整理成 worklog，要我幫你寫嗎？」

---

## 注意事項

- 逐字稿口語錯字可自行修正，不需保留原始措辭
- 專案歸屬不明確時標註 `【待確認】`，不要自行假設
- 處理完的逐字稿不要刪除，保留在 `minutes/` 作為原始資料
- 寫 worklog 時若涉及 LL 宇宙或 colombo 個人創業，**不要寫進來**（守治理層定位的邊界）
