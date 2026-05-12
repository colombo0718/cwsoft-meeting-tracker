# cs-shadow 空白草稿根因 × gtb.py 中文亂碼大掃除

- 日期：2026-05-11（晚上，承接同日 sqlgate / aquan 兩篇之後）
- 主機：公司主機（pos@DESKTOP-P5EBFBE）
- 參與者：colombo0718 × Claude (claude-opus-4-7[1m])
- 相關專案：cwsoft-ai-customer-service、general-task-bot、cwsoft-super-manager

> 承接 [2026-05-10-cwsoft-vision-synthesis-and-archival.md](2026-05-10-cwsoft-vision-synthesis-and-archival.md)
> （戰略層藍圖入帳）之後第一個技術問題。user 從 dashboard 看到 cs-shadow 跑著但
> 影子訊息表裡近期 ai_draft 都空白 — 「客服 AI 看起來活著但不會寫草稿」。

---

## 一、起點：影子模式沒生草稿

user 描述：「AI 客服影子模式，他現在的問題是，一堆近來的訊息他都沒有寫出回覆草稿」。

cs-shadow 是 gtb_dev.py 跑的，模式 `shadow` — mirror 真客服流量、跑分類抽欄位、生 AI 草稿，
但**不回 LINE**。草稿寫進 `shadow_messages` 表給人工審閱，是上 production 前的測試手段。
草稿空白 = LLM 沒回東西 = 整個影子模式失去意義。

---

## 二、走錯第一步：誤判 worker.leaflune.org

第一個假設：cs-shadow 透過 remote_worker provider 打 `worker.leaflune.org` 拿 LLM 結果。
我先去看 cloudflared logs、跑 `curl worker.leaflune.org/llm` 想看回什麼 — 結果 530 error。

**錯了**。再看 gtb_dev.py：

```python
PROVIDER = "groq"
LLM_MODEL = "llama-3.3-70b-versatile"
```

cs-shadow 走 **groq**，不是 remote_worker。worker.leaflune.org 是另一條路線
（aquan-manager 用），跟 cs-shadow 無關。

直接打 groq API 驗證 — 正常回 200，response 有內容。**provider 沒壞**。

教訓：被「530 error 很顯眼」帶歪。下次先 trace code 看實際 provider，再決定查哪條路。

---

## 三、真正根因：run_extractor 漏掉 prompt_template

抓 cs-shadow 的 log，看到典型 trace：

```
intent: null
[SHADOW] 已儲存，ai_draft=...
```

`extracted_intent` 一律是 `null` — 意圖分類全部失敗。null 進到 classify_tree 走 fallback 分支，
fallback task 沒 action，所以 `ai_draft` 空白。

**對比 gtb.py 跟 gtb_dev.py 的 `run_extractor` 函式**：

| 行為 | `gtb.py`（正式版，prod 阿全在跑）| `gtb_dev.py`（dev 引擎，cs-shadow 跑） |
|---|---|---|
| 組 prompt | format + ref_block + **prompt_template** + 使用者訊息 | format + ref_block + 使用者訊息 |

`gtb_dev.py` 漏了 `parts.append(prompt_template.strip())`。LLM 收到的 prompt 結構：

```
[輸出格式說明]

[參考資料]

使用者訊息：標籤機去哪設定？
```

**沒有任務描述**。LLM 不知道要做什麼分類，回 null 完全合理 — 它連「這是分類任務」都不知道。

修法：補回那一行：

```python
parts = []
fmt_prompt = _pick_format_prompt(with_confidence)
if fmt_prompt:
    parts.append(fmt_prompt)
if ref_block:
    parts.append(ref_block)
parts.append(prompt_template.strip())   # ← 補回這行
parts.append(f"使用者訊息：{user_input or ''}")
raw = llm_complete("\n\n".join(parts))
```

commit：`e48fe8e` in general-task-bot。

驗證：user 重新傳「標籤機去哪設定」測試 → 影子表裡 intent 正確分到 `queryKB`，
AI 草稿生出 KB 比對結果。**正式恢復**。

---

## 四、為什麼這個 bug 能潛伏

`prompt_template` 是任務描述本體（從 prompts_cs.ini 拉的「你是分類器，請判斷使用者意圖屬於以下哪一類…」）。
漏掉之後 prompt 只剩格式說明跟參考資料 — LLM 還是會「回東西」，回的就是 `{"intent": null}`。

`null` 通過 `mission_data["classify_tree"]["branch"]` 比對到 `"match": "null"` 的 fallback 分支，
**程式不會 raise，dashboard 看到 service running，看不出有問題**。只有從 shadow_messages
表的 ai_draft 欄位空白才看得出來。

這是個典型「silent degradation」— 服務沒掛、health check 綠燈、但邏輯壞掉。教訓：
**health endpoint 健康 ≠ 業務邏輯健康**。未來 shadow 模式應該加個「近 N 筆 ai_draft
空率 > X%」的監控，這種 bug 才會被 dashboard 抓到。

---

## 五、附帶工程：gtb.py 中文亂碼大掃除

修完 gtb_dev.py 之後 user 補一刀：「`gtb.py` 還有一些中文亂碼你修正一下」。

打開 gtb.py 看 — 大量 cp950→UTF-8 誤讀的「雿輻撓伐」型亂碼，散在：

- 第 211/228/245/269 行：各 LLM provider 函式的 fallback message「（沒有回覆）」
- 第 324 行：`run_extractor` 的 `f"使用者訊息：{user_input or ''}"`
- 第 568/581/584/588/603/606/613/622/623/625 行：影子模式內部註解

### 修復策略

user 給了指引：「真的有反推不出來的，就看一下程式上下文，然後刪掉重寫註解吧」+
「或者也可以參考他的前輩 main.py 晚輩 gtb_dev.py」。

對應到三類處理：
1. **能從 main.py 直接抄的**（fallback message）→ 抄
2. **能從 gtb_dev.py 對照的**（影子模式註解，gtb_dev.py 邏輯一樣但中文未亂碼）→ 抄
3. **真亂到反推不出來的** → 看程式上下文重寫

寫一個 Python script 按行號做批次替換，比 Edit tool 對亂碼字串做 anchor matching 穩。

### 附帶清掉的兩個雷

- **BOM**：gtb.py 開頭有 UTF-8 BOM，gtb_dev.py 沒有。對齊掉。
- **docstring `\U` 語法錯誤**：原 docstring 寫了 `C:\Users\pos\Desktop\...` Windows 路徑，
  Python 把 `\U` 當 unicode escape 解，補完亂碼後 `ast.parse` 直接報
  `'unicodeescape' codec can't decode bytes in position 227-228: truncated \UXXXXXXXX escape`。
  修法：docstring 前加 `r` 前綴變 raw string。

commit：`b3609cb` in general-task-bot。

---

## 六、push 卡關 — wincredman 老問題

兩個 commit（`e48fe8e` + `b3609cb`）都在 local master 上，origin master 還停在 4/6 `0250eb0`。

`git push` 嘗試三次：bash / PowerShell / 都報 `Unable to persist credentials with the 'wincredman' credential store` + `/dev/tty: No such device or address`。

SSH/headless session 沒 TTY，wincredman 不能輸入帳密；也沒裝 `gh` CLI、也沒設
`GH_TOKEN` env。**這個機器目前的設定下，Claude 沒辦法自己 push**。

短期：user RDP 過去手動 push。
長期：考慮設 PAT 進 user env（`setx GH_TOKEN <token>`）+ 改 remote 用 token-in-URL，
讓 SSH session 也能 push。

---

## 七、本日成果

### general-task-bot
- `e48fe8e` fix: `gtb_dev.py` `run_extractor` 補回漏掉的 `prompt_template`
- `b3609cb` fix: `gtb.py` 修中文亂碼 + 移除 BOM + docstring 改 raw string
- ⚠️ 兩個 commit local-only，尚未 push

### cwsoft-ai-customer-service / cs-shadow service
- 影子模式 AI 草稿正常恢復生成
- user 親測「標籤機去哪設定」正確分類到 queryKB

### matrix-manager
- 本檔 `meetings/2026-05-11-cs-shadow-empty-drafts-and-gtb-encoding-cleanup.md`
- INDEX.md 同步更新

---

## 八、待跟進

### 立即
- [ ] user RDP 過去 push general-task-bot 兩個 commit 到 origin

### 短期
- [ ] cs-shadow 加「近 N 筆 ai_draft 空率」監控，避免下次 silent degradation 沒人發現
- [ ] aquan-manager（也跑 gtb.py 但是 prod）的近期訊息抽樣檢查 — 雖然 gtb.py 沒漏 prompt_template，但亂碼修了那麼多行，要驗一下 prod 行為沒走樣

### 中期
- [ ] 評估設 PAT 進 user env，讓 Claude SSH session 能自己 push（root cause 解決 push 卡死）
- [ ] general-task-bot 的 `.gitignore` 檢查 — 本次 commit 看到一堆 modified（main.py / PROJECT.md / customerlist.txt / todo_list.db）跟 untracked（benchmark_report*.json、boss_chat.txt、docs/）累積很久，找時間整理

---

## 附：當天的關鍵推導

### 「為什麼一開始走錯到 worker.leaflune.org」

只看「最近改過什麼可能會影響 cs-shadow」的直覺，沒先確認 cs-shadow 的 provider 設定。
**provider 是 hardcoded 在 gtb_dev.py 頂端**，5 秒就能確認，卻沒先看 → 浪費約 10 分鐘
查 cloudflared / worker 那條無關路徑。

教訓：debug 服務時第一動作是 trace code 找「實際呼叫哪個外部 endpoint」，不是
猜「最近哪個元件可能壞」。

### 「為什麼 gtb_dev.py 漏 prompt_template 沒人發現」

兩個原因疊加：
1. `null` 是合法分類結果（fallback 分支設計就是收 null），程式不 raise
2. shadow 模式本來就「不回覆」，user 不會立刻發現 — 是事後查 shadow_messages 才看出

這是 silent degradation 的教科書範例。**設計階段應該預期到「LLM 持續回 null」是個
高機率 failure mode**，shadow 模式特別需要監控分類成功率。

### 「為什麼 gtb.py 修亂碼還要連帶處理 BOM 跟 docstring」

修完亂碼 `ast.parse` 失敗，第一直覺是「我寫的某個替換漏了」— 跑 grep 找不到。
看 error message 才注意到 `\U` — 原來是 docstring 的 Windows 路徑。

BOM 是順手：gtb.py 有 BOM、gtb_dev.py 沒 BOM，兩個版本對齊 diff 看起來很雜，
乾脆統一掉。

教訓：碰到「我寫的部分都對啊」的 syntax error，要看 error message 指的具體位置，
不要假設 bug 一定在自己改的範圍。
