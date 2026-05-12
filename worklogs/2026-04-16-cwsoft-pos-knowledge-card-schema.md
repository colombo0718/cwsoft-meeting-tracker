# cwsoft POS 知識卡 schema 與 Agent 調度邊界

- 日期：2026-04-16
- 角色：使用者 / Codex (GPT-5)
- 相關專案：cwsoft-ai-customer-service、general-task-bot、cwsoft-sqlgate、cwsoft-aquan-manager、autoQuotes、POS3

---

## 1. 事實來源與知識庫定位

**結論**：知識庫不是讓 LLM 自由理解，而是要綁定三個事實層。

| 事實層 | 內容 | 作用 |
|------|------|------|
| 程式碼 | POS3 完整 VB.NET 程式碼 | 反映系統現在實際怎麼運作 |
| 資料庫 | SQL Server schema + 工程師整理說明 | 反映資料結構、SP、Trigger、資料流 |
| 老闆 knowhow | 透過 GTB + LINE OA 與老闆互動沉澱 | 補足設計意圖、歷史包袱、例外規則 |
| 巡檢截圖 | POS 安裝版自動巡覽全部選單截圖（183 個葉節點） | 補足程式碼無法反映的 UI 介面細節：畫面佈局、按鈕位置、實際操作流程 |

> **補充說明（2026-04-16）**：POS3 是 VB.NET / WinForms 舊式架構，光讀程式碼能理解邏輯，但無法還原實際畫面長什麼樣、操作步驟怎麼走。巡檢截圖腳本（`巡檢截圖.py`）透過 `WM_COMMAND by ID` 觸發所有功能並截圖，成為這個事實層的素材來源。相關技術細節見 `2026-03-24-cwsoft-pos-inspection-screenshot.md`。

知識庫要讓 Agent 持續建立、更新、疊代，但所有知識都必須能回溯到上述事實來源，避免產生幻覺。

---

## 2. 應用層分工

**結論**：同一套知識底座要支撐三個應用層。

| 應用層 | 主要用途 | 備註 |
|------|------|------|
| 客戶服務 | 對客戶回覆、客服輔助、有限的客戶自身資料查詢或操作 | 需先確認身分與權限，且只能碰該客戶自己的資料庫 |
| 工程師輔助 | 排查、查 schema、查程式邏輯、查設計意圖 | 偏分析與定位，不等於直接執行 |
| 業務輔助 | 支援老闆與業務的營運、查詢、流程協助 | 會串 cwsoft-aquan-manager、cwsoft-sqlgate、autoQuotes |

---

## 3. 執行層責任劃分

**結論**：知識庫與資料庫讀寫要分開。

- 知識庫負責理解、說明、判斷依據。
- GTB 負責調度任務與 prompt 組裝。
- 所有資料庫讀寫都走 `sql_gate`，不直接由知識庫承擔。
- Agent 可以根據知識庫內容理解，動態優化、新增、刪減 `sql_gate` 的功能，但執行責任仍在 `sql_gate`。

一句話整理：知識庫是腦，`sql_gate` 是手，GTB 是神經系統。

---

## 4. 知識卡 schema 定案

### 4.1 先前討論

一開始曾考慮把內容直接塞進 schema，但後來確認這樣不利於：
- 人工 review
- 單張內容修改
- Git diff 與長期維護
- 避免單一檔案過大

### 4.2 定案

**知識卡 schema 採 metadata-only，不直接包含正文內容。**

定案的 7 個欄位如下：
- `id`
- `topic`
- `content_ref`
- `sources`
- `status`
- `updated_at`
- `apps`

欄位含義：
- `id`：穩定識別碼。
- `topic`：主題名。
- `content_ref`：指向實際知識內容 `.md` 檔案的路徑。
- `sources`：來源陣列，記錄 `code` / `db` / `boss_qa` / `doc` / `screenshot` 等來源。
- `status`：知識狀態，建議使用 `draft` / `verified` / `conflicted` / `archived`。
- `updated_at`：最後更新時間。
- `apps`：此卡可供哪些應用層使用，例如 `customer_support`、`engineer_assist`、`business_assist`。

### 4.3 為何不把內容放進 schema

**結論**：內容與 schema 要分開。

- schema 只放 metadata，比較像可機器調度的卡片目錄。
- 內容本身一張卡一個 `.md`，方便人工檢查、Agent 更新、版本比對。
- 這樣不需要在大型 JSON 內「大海撈針」。

---

## 5. 是否需要額外 knowledge index

**結論**：現階段先不要做獨立 index。**

原本曾考慮多做一層 selector -> card ids 的 `knowledge_index`，但目前先不採用，理由是：
- 會多一層維護成本
- 如果 schema 已經能定位 `content_ref`，再多一層會變成「指來指去」
- 現階段以簡潔、可維護為優先

目前暫定：
- 直接由 Agent / API 讀 schema 集合後篩選
- 需要時再依 `id`、`topic`、`apps`、`sources` 等欄位定位
- 未來若真的出現固定 selector 對多卡組包需求，再補 index

---

## 6. 與 GTB 的相容原則

**結論**：知識卡 schema 與 GTB config 要相容，但不是同一件事。**

GTB 現在的結構是：
- `prompts*.ini`：負責 extractor prompt
- `mission*.json`：負責 classify tree、fields、action url_template

以 AI 客服為例，目前是用 `sections=3-1` 這種章節編號做 selector。這種 selector 應保留在 GTB / API 調度層，而不是塞進知識卡 schema。

也就是：
- 知識卡 schema：描述一張卡的 metadata 與來源
- 知識內容 md：放實際內容
- GTB config：決定怎麼抽 selector、怎麼調 API、怎麼組 prompt

現階段先維持：
- GTB 繼續用 `sections` 這種簡單 selector
- 新知識卡結構先平行建立，不碰現有 AI 客服流程

---

## 7. 現有知識庫可否轉成新架構

### 7.1 kb-customer

**結論**：大多可以直接整理成新架構。**

原因：
- 檔案結構規律
- 標題層級穩定
- 內容大多已是客服可用知識

適合的做法：
- 不改原始 md
- 另外產生知識卡 metadata
- 內容仍拆成一張卡一個 md
- 一個章節可能對應多張卡，例如 overview / workflow / faq / notes

### 7.2 kb-engineer

**結論**：只能部分直接整理。**

可直接整理的：
- `客戶_資料庫說明.md`
- `POSConfig_資料庫說明.md`
- 其他人工整理的工程師說明檔

不適合直接整份轉卡的：
- `db_schema_*.md` 這類 raw schema 匯出檔

原因：
- raw schema 更像來源庫，不是直接給 LLM 回答的知識卡
- 這類檔案應先保留為 `sources`，再按需求抽卡

---

## 8. 目前暫定資料結構方向

```text
knowledge/
  catalog/
    knowledge_cards.json
  cards/
    customer_support/
      ...單張卡內容.md
    engineer_assist/
      ...單張卡內容.md
    business_assist/
      ...單張卡內容.md
```

目前只定兩個概念：
- `knowledge_card_schema`
- `knowledge_content_file`

暫不建立：
- `knowledge_index`

---

## 9. 事實層的雜訊與設計哲學

**結論**：四個事實層不是「權威真相」，而是「現有最佳近似值的集合」。

每一層都有各自的典型雜訊：

| 事實層 | 典型雜訊 |
|-------|---------|
| 程式碼 | bug、dead code、命名誤導、歷史遺留邏輯 |
| 資料庫 | 棄用欄位、設計意圖遺失、SP 副作用難追 |
| 老闆 knowhow | 記憶模糊、語音辨識偏差、知識缺口自己不知道 |
| 巡檢截圖 | 只反映當前版本 UI，不含邏輯意圖、狀態分支 |

這個混沌不是缺陷，而是設計前提。知識庫的定位比較像**偵探檔案夾**，不是教科書——目標不是每張卡都是真理，而是讓 Agent 在混沌裡有足夠的線索可以推理，且知道自己的推理有多不確定。

因此幾個設計方向值得納入：

1. **不強求單一真相** — 卡片可以並列「程式碼顯示 X，但老闆說實際是 Y」，讓下游應用層自行決定怎麼用。
2. **信心度標記** — 現有 `status` 欄位的 `conflicted` 狀態要搭配說明「哪兩個來源打架、打在哪裡」，未來也可考慮加 `confidence: low / medium / high` 反映交叉驗證程度。
3. **來源衝突顯性化** — 多源一致時信心提升，來源打架時應顯性標記，而非靜默選一。

---

## 10. 圭臬層（Guardrails）— 凌駕事實與知識的行為邊界

**結論**：未來需要在事實層與知識卡層之上，建立一組不可撼動的絕對原則。

三層架構：

```
圭臬層（Guardrails）   ← 不可撼動，Agent 無論推理出什麼都不得逾越
    ↑
知識卡層（Knowledge）  ← 有噪音、有信心度、可更新
    ↑
事實層（Facts）        ← 四個來源，各有缺陷
```

圭臬與知識卡的本質差異：知識卡衝突時 Agent 可以推理、選擇、標記 `conflicted`；圭臬碰到就停，不推理、不例外。

初步分類方向：

| 類別 | 例子 |
|-----|-----|
| 業務安全 | 不得刪除或竄改客戶交易紀錄、不得洩漏客戶資料 |
| 系統安全 | 不得執行無 WHERE 條件的 bulk update/delete、不得觸發全表掃描造成伺服器巨量負擔 |
| 不可回溯操作 | 日結帳、庫存歸零、跨分店調帳等，執行前必須人工確認 |
| 財務誠信 | 不得繞過進銷存流程直接修改庫存數字或金額 |

**目前狀態**：概念確立，尚未實作。後續需決定圭臬以何種形式存在（獨立設定檔、system prompt 固定段落、或 Agent 初始化時強制載入的規則集）。

---

## 11. 後續工作

- [ ] 在不影響現有 AI 客服使用的前提下，平行建立新知識卡結構
- [ ] 先盤點 `kb-customer` 可直接拆卡的規則
- [ ] 再盤點 `kb-engineer` 中哪些檔案屬於可直接拆卡、哪些只能當來源
- [ ] 後續再決定 Agent 生成與更新知識卡的實作流程

---

## 附：決策推導過程

> 以下為本次討論的思路推導過程，記錄「為什麼做出這些決策」。

### 推導鏈摘要

```
現有客服章節知識庫不夠支撐長期理解
→ 知識必須綁程式碼 / DB / 老闆 knowhow 三個事實層
→ 同一套知識底座要支撐客服 / 工程師 / 業務三個應用層
→ 知識庫、GTB、sql_gate 必須拆責任
→ 知識卡要給 Agent 維護，也要給人類 review
→ schema 與內容必須分開（可讀性與可維護性是第一級需求）
→ 先不要多做 knowledge_index（schema 已能定位，多一層是指來指去）
→ 形成 metadata-only 7 欄 schema
```

### 幾個關鍵轉折

**事實層的性質**：四個事實層不是「權威真相」，而是「現有最佳近似值的集合」。知識庫比較像偵探檔案夾，不是教科書——目標不是每張卡都是真理，而是讓 Agent 在混沌裡有足夠的線索可以推理。

**schema 不含正文的原因**：這套知識系統預期會被 Agent 持續維護，也有人類持續 review，所以可讀性與可維護性是第一級需求，不是設計理論問題。

**小豪的角色定位**：老闆 knowhow 層需要透過互動沉澱，小豪（數位分身）在現實工作中本來就同時涵蓋進度匯報、POS 理解、向老闆備詢，因此自然成為 `boss_qa` 來源的前台互動入口。對外是同一個人格，對內進度記憶與知識記憶仍要分開。

**knowledge_index 為何先拿掉**：多一層索引看起來合理，但使用者問了一個精準問題：如果 schema 本身已經能靠 `id / topic / apps / sources / content_ref` 定位，為什麼還要再多一層指來指去？刻意選擇簡化，不是遺漏設計。
