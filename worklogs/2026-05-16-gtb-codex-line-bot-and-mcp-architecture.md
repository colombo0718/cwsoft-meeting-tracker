# gtb_codex.py LINE bot 上線、對話完整化、log 重組、MCP+Principal 長期架構規劃

- 日期：2026-05-16
- 主機：公司主機
- 參與者：colombo0718 × Claude (claude-opus-4-7)
- 相關專案：general-task-bot、cwsoft-aquan-manager、跨專案

---

## 討論摘要

### 1. gtb_codex.py 接上 LINE OA「阿全經理(測式)」

**背景**：5/15 那天我們把 codex 單一 session 的 prototype 寫完（gtb_codex.py），colombo 在 LINE Developers Console
為新 OA `@526fdbzo` 設好 webhook URL `https://cwsoft.leaflune.org/callback/@526fdbzo`，super manager 那邊把 6010 對外暴露。

**結果**：實際打 LINE 通了、跟 codex 聊了大約 36 turn（包含「設秘密 banana42」的記憶測試 + 試列檔失敗 + 用途確認）。

---

### 2. Bug 找出：codex 多段 reply 在 LINE 被砍剩最後一句

**症狀**：colombo 在 LINE 看到的 codex 回覆只有最後一行，但 codex 實際輸出是多段完整回答。

**Root cause**：`gtb_codex.py` 的 `_parse_codex_reply` 寫了一個 regex `\ncodex\n(.*?)\ntokens used` 試圖從 stdout 擷取 reply。
這個 pattern 是針對「`2>&1` 合併過的 stderr+stdout 格式」設的，但 `subprocess.run(capture_output=True)` 會把 stdout / stderr 分開捕：
- stderr：metadata（header / `session id` / `codex` 標籤 / `tokens used`）
- stdout：**純粹 reply 文字本身**

regex 永遠在 stdout 裡 match 不到 → 走 fallback 取「最後一行非空」→ 多行 reply 被砍剩最後一句。

**修法**：`_parse_codex_reply` 簡化成 `return (stdout or "").strip()`，根本不需要 regex。

**驗證**：強制 codex 三段回覆，三段完整出現、字數對。

---

### 3. session 持久化：Flask 重啟後對話不掉

**動機**：colombo 問「不能就還是打同樣的 SID 嗎」——之前每次 Flask 重啟都 mint 新 session，先前對話通通遺失。

**做法**：
- Boot 順序改為 4 階：`--session-id` > `--fresh` > `.gtb_codex_session` 檔有 SID > 都沒有才 mint
- 把 SID 持久化到 `cwsoft-aquan-manager/.gtb_codex_session`（一行純文字）
- `/reset` endpoint 改成清檔 + mint 新的

**驗證**：寫進「19:00 那條 LINE 對話的 session」`019e2c02-...-5aa1`、重啟、問「之前的暗號是什麼」→ 正確回 `banana42`。

---

### 4. 完整對話 log writer：`<sid 前 8 碼>_chat.log`

**動機**：colombo 想留完整雙方對話紀錄、之前只有 `[WEBHOOK] msg=...` 跟 access log，reply 內容沒記。

**設計**：
- 一個 codex session 一個檔，命名 `<session_id 前 8 碼>_chat.log`（跟 `~/.codex/sessions/.../rollout-*-<sid>.jsonl` 用同 prefix、grep 一下兩邊都找得到）
- 寫進 `cwsoft-aquan-manager/logs/`
- 格式：
  ```
  [YYYY-MM-DD HH:MM:SS] USER line:U34e... 或 sim: <text>

  [YYYY-MM-DD HH:MM:SS] BOT line:U34e... (5.6s):
      多行 reply 縮排 4 格
      (空行用空白行表示)
  ```
- Threading lock 確保並發安全
- /callback 跟 /sim 兩個 endpoint 都會寫

---

### 5. cwsoft-aquan-manager root 的 28 個 .log 檔搬進 logs/

**事件**：colombo 看到 root 一堆歷史 baseline log 檔散落，要求整理進 `logs/` 子資料夾。

**動作**：
- 建 `cwsoft-aquan-manager/logs/`
- `mv *.log logs/`：26 個歷史 benchmark log 直接成功
- 2 個運行中的 `gtb_codex.log` / `gtb_codex.err.log` 被 PowerShell exclusive lock 卡住 → 停 Flask → mv → 重啟 redirect 到新路徑
- 重啟之後 session 自動 resume（持久化機制這時剛好驗證）、對話銜接無縫

---

### 6. codex CLI 沙箱探索：找到 Windows-specific bug

**緣起**：LINE 上 colombo 問 codex「列 cwd 檔案」、codex 試 PowerShell 全失敗。逐層 debug 才發現問題不是權限不夠，是 codex on Windows 的沙箱踩到 PowerShell DLL init bug。

**完整測試結果**：

| codex 沙箱設定 | 結果 |
|---|---|
| `-s read-only`（exec 預設）| Codex 政策層直接擋掉所有 shell exec → `blocked by policy` |
| `--full-auto` (= `-s workspace-write -a never`) | shell 政策放行了，但 PowerShell.exe 在 Windows job-object sandbox 下 DLL init failed (0xC0000142、18ms 內死) |
| `--full-auto -c windows.sandbox=elevated` | 嘗試提權至管理員、卡 UAC 彈窗無人應、4 分鐘沒回應 |
| **`--dangerously-bypass-approvals-and-sandbox`** | **完整列出 cwd**（14 個檔案/資料夾）|

**結論**：在「Flask spawn codex spawn PowerShell」的巢狀環境下，**Windows codex 唯一能 shell 的選項是完全關沙箱**。
這該回報給 codex 上游、可能是 Windows 平台的 known issue。

**短期不採用 `dangerously-bypass`**：colombo 提了更好的方向（見下節）。

---

### 7. 「綁手綁腳但餵它念的」capability-restricted 設計（colombo 拍板的方向）

**colombo 原話**：

> 「shell 不給用、我自己作工具包給他用。例如不給看路徑、我就作一個看路徑、讀所檔名給他聽的腳本。
> 你把 codex 手腳綁起來、眼睛還矇起來，我就找人念給她聽。」

——這是業界俗稱的 **capability-restricted agent** 設計：codex 完全不能 shell、不能瀏覽檔案系統，
只能透過我們手寫的、安全的工具去獲取資訊。每個工具就是「念給它聽的人」。

**實作方式對照**：

| 路線 | codex 自主權 | 實作工 | 可長期擴展 |
|---|---|---|---|
| MCP server | ✓ codex 自己決定何時用 | 中（~100 行 + config）| ✓ |
| API（HTTP route）注入 prompt | ✗ gtb_codex grep keyword 預判 | 低 | △ |
| CLI script 注入 prompt | ✗ 同上 | 最低 | △ |

**colombo 選 MCP**，因為要的就是「阿全有自主性」——這是 MCP 的設計強項。

---

### 8. Principal-based 多租戶授權架構（長期規劃）

接著 colombo 拋出更大格局的問題：

> 「我能進一步詳細限定他在什麼狀況能用哪些 mcp 的哪些功能嗎？跳出阿全經理的框架，
> 如果之後客服 ai 也用這套 mcp、當他面對不同層級客戶的時候、有些 mcp 就能用、有些就不能用」

進一步：

> 「current_role 只能綁定 session id 嗎、能不能再加上根據 user id 作變化？
> 例如之後我把到資料庫查資料也作成 mcp、我要知道她的資料庫是哪個、只能查自己資料庫、不能查別人的呀」

這是兩件事疊加：
1. **RBAC**（功能權限）：role 決定能不能用某 tool
2. **Multi-tenant data scoping**（資料範圍）：tool 內看 principal 的 tenant_id / db_name 決定能看誰的

**結論**：MCP 規範本身沒這個 ACL、要疊在上層自己做。發展出「**Principal**」這個身份卡概念
（含 role / tenant_id / db_name / scopes / line_user_id 等多欄位）、tool 端從 principal 拉識別、不接 caller 帶。

**完整架構規劃整理在另一份文件**：[`cwsoft-project-tracker/docs/cwsoft-ai-mcp-and-principal-architecture.md`](../docs/cwsoft-ai-mcp-and-principal-architecture.md)

---

## 本輪新增 / 更新檔案

### general-task-bot
- `gtb_codex.py`
  - `_parse_codex_reply` 改成直接 `stdout.strip()`、不再 regex
  - 加 `--session-id` / `--fresh` CLI flag
  - 加 SESSION_FILE 持久化邏輯（boot 4 階順序）
  - 加 `--codex-sandbox` flag（預設 `workspace-write`、暫不啟用 dangerous-bypass）
  - mint 跟 resume 的 codex 命令都接受 sandbox 旗標、resume 透過 `--full-auto` 提權
  - 加 `log_chat_turn` writer + `<sid 前 8 碼>_chat.log` 寫到 `logs/`

### cwsoft-aquan-manager
- 建 `logs/` 子資料夾、28 個歷史 .log 全搬進去（含 v1-v5 baseline 跑題輸出 + gtb_codex 運行 log）
- 新增 `.gtb_codex_session`（一行 SID 持久化檔、無 git）

### cwsoft-project-tracker
- `docs/cwsoft-ai-mcp-and-principal-architecture.md`（新）：MCP + Principal 完整架構規劃

---

## 待跟進

- [ ] 決定 gtb_codex.py 預設沙箱：純對話保留 `read-only` / 走 capability-restricted 配 MCP / 暫時開 `dangerous-bypass` ——三選一
- [ ] **寫第一個 MCP server**（30-50 行 prototype，1-2 個 tool 驗 codex 能 discover 能 call）
- [ ] 設計 `principals.json` 第一版（先把 colombo 自己一個 owner 寫進去）
- [ ] gtb_codex.py 加 setup_context 機制：每收 LINE 訊息、由 line_user_id 查 principal、塞給 codex 之前先注入
- [ ] 寫一個 `scripts/dump_codex_session.py` 把任意 session jsonl dump 成可讀 chat 對話（之前 ad-hoc 寫過、該正式 commit）
- [ ] codex on Windows 的 PowerShell DLL init 0xC0000142 issue 確認是上游 bug、考慮回報
- [ ] LINE 「阿全經理(測式)」typo 改成「測試」（colombo 提過、還沒去 LINE Console 改）
