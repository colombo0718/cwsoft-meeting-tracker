# worklogs/ — 人對 AI 工作紀錄

> 這個目錄收 colombo 跟 AI（主要是 Claude Code）協作推進 CWSoft 工作的紀錄。
> 跟 `meetings/`（人對人會議逐字稿整理）平行存在，但**性質不同**：
>
> - `meetings/` — 多人會議的決議追蹤（雅婷逐字稿 → 結構化會議紀錄）
> - `worklogs/` — colombo + AI 協作的設計 / 實作 / 思考過程紀錄

---

## 命名規範

```
worklogs/YYYY-MM-DD-主題.md

例：
  2026-05-08-cwsoft-customer-service-first-execution.md
  2026-04-14-gtb-confidence-and-benchmark-roadmap.md
  2026-04-28-gtb-local-llm-model-selection.md
```

主題用英文、kebab-case、簡潔描述。

---

## 內容結構建議

```markdown
# 主題標題

- 日期：YYYY-MM-DD
- 參與者：colombo × Claude (model name)
- 相關專案：cwsoft-pos / gtb / 小葳客服 / 其他

> 一段引言：這次討論的起點與重點

---

## 一、起點 / 動機

## 二、討論內容

## 三、決策 / 設計

## 四、待對齊事項

## 五、本次產出檔案清單

| 路徑 | 類型 | 說明 |
|------|------|------|

---

## 一句話總結
```

---

## 讀者

```
✓ colombo（自己回顧）
✓ 老闆（透過 AI 查資訊部門工作細節）
✓ 未來 AI session（接班讀 context）

→ 寫的時候要假設「老闆會用 AI 來查這篇」
→ 不要寫純技術 jargon 不解釋
→ 重要決策要寫 why（不只 what）
```

---

## 跟 meetings/ 的差異

| 維度 | `meetings/` | `worklogs/` |
|------|-------------|-------------|
| 參與者 | 多人（同事 / 客戶） | colombo + AI |
| 來源 | 雅婷逐字稿整理 | 即時對話過程 |
| 結構 | 標準會議模板（決議 / 待辦） | 思考脈絡（討論 → 設計 → 結論） |
| 主要讀者 | 與會者 / 老闆 | colombo / 老闆 / AI |
| 觸發頻率 | 有會議才有 | colombo 跟 AI 推進任務時 |

---

## 既有紀錄會從哪裡來

```
過去 30+ 篇 colombo × AI 的 CWSoft 工作紀錄
目前混在 matrix-manager/meetings/ 內
（因為早期 LL 跟 CWSoft 治理沒分開）

→ 接下來會分批搬過來
→ 例：cwsoft-pos-* / gtb-* / cwsoft-customer-service-* 等
→ 搬完後 matrix-manager/meetings/ 只留 LL 內容
```
