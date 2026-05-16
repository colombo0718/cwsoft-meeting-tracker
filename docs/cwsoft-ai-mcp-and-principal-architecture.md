# CWSoft AI 服務系統：MCP + Principal 授權架構規劃

> 涵蓋 **GTB（內部老闆助手「阿全經理」）** 與**未來客服 AI**（對外、不同層級客戶）共用的 tool / 授權底層架構。
> 目標：一份 MCP 工具集 + 一份 Principal 身份卡規格、撐起多 AI 多租戶場景。
>
> 撰寫日期：2026-05-16
> 對應 worklog：[2026-05-16-gtb-codex-line-bot-and-mcp-architecture.md](../worklogs/2026-05-16-gtb-codex-line-bot-and-mcp-architecture.md)

---

## 1. 為什麼要這套

CWSoft 短期會出現至少 4 種 AI 場景，每種對「能做什麼」「能看什麼」的權限差異很大：

| AI 場景 | 對象 | 該能做什麼 | 不該能做什麼 |
|---|---|---|---|
| 阿全經理（內部）| colombo / cwsoft 員工 | 改任何客戶資料、看所有 DB、改設定 | （沒有限制）|
| 客服 - VIP 客戶 | 升級方案的客戶 | 查自己訂單、查自己歷史、改自己聯絡資訊 | 看別人資料、改 cwsoft 設定 |
| 客服 - 一般客戶 | 標準方案 | 只查自己最新訂單、看 FAQ | 看歷史資料、改任何資料 |
| 客服 - 未綁定 / 陌生人 | 任何 LINE 進來但沒登入 | 看 FAQ、店鋪時間 | 任何個資 |

**共同需求**：
- 用同一套 codex 引擎（不想為每種對象訓練不同模型）
- 用同一份「工具實作」（DRY，不想各寫一套）
- **不同對象進來、自動分流到該有的權限**

不靠這套架構就會走向「每個 AI 自己 fork 一份程式」的災難。

---

## 2. 兩個核心概念

### 2.1 MCP（Model Context Protocol）

Codex / Claude / Cursor 等多家 LLM agent 工具支援的「**外掛 tool 標準協定**」。
我們寫一個 MCP server（Python / TS）暴露一組函式、註冊在 `~/.codex/config.toml`、
codex 啟動時自動 discover、推理過程中自主呼叫。

```toml
[mcp_servers.cwsoft_tools]
command = "python"
args    = ["-m", "cwsoft_ai_tools.server"]
cwd     = "C:\\Users\\pos\\Desktop\\cwsoft-ai-tools"
```

技術細節：tool 是一個有 docstring + type hints 的 Python 函式、SDK 自動轉 schema 給 LLM。

**MCP 規範本身沒有 ACL**——所有 tool 對連線的 client 都是公開的。
RBAC 要疊在我們自己的程式邏輯上。

### 2.2 Principal（身份卡）

每次 codex 收到訊息背後**真正的呼叫者**的識別包：

```python
{
    "role":         "vip_customer",            # 用來決定能不能 call 某 tool
    "tenant_id":    "前進通訊",                  # 用來決定看誰的資料
    "db_name":      "Customer_QianJin",        # 對應的後端 DB
    "scopes":       ["own_orders", "own_invoices"],   # 細粒度子權限
    "line_user_id": "U99xy7d30bc...",          # 來源辨識
    "session_id":   "019e2c43-...-d592",       # 對應 codex session
}
```

每個 MCP tool 進來的第一件事就是查 principal 決定：
1. **能用嗎？**（role / scopes）
2. **看誰的資料？**（tenant_id / db_name；不接 caller 帶）

---

## 3. 架構大圖

```
                  ┌─────────────────────────────────┐
                  │        LINE / 其他入口            │
                  │  (老闆 / 員工 / VIP / 一般客戶)    │
                  └──────────────┬──────────────────┘
                                 │ webhook
                                 ▼
                  ┌─────────────────────────────────┐
                  │   gtb_codex.py（或 cs_codex.py） │
                  │   - 認 line_user_id              │
                  │   - 查 principals[user] → role 等 │
                  │   - 通知 codex「你現在是 X 身份」  │
                  └──────────────┬──────────────────┘
                                 │ exec resume <SID>
                                 ▼
                  ┌─────────────────────────────────┐
                  │    codex（gpt-5.4 / 其他）       │
                  │    - discover MCP tools          │
                  │    - 自主決定何時呼叫哪個 tool    │
                  └──────────────┬──────────────────┘
                                 │ MCP stdio
                                 ▼
                  ┌─────────────────────────────────┐
                  │  cwsoft-ai-tools（MCP server）    │
                  │  - 收到 tool call                │
                  │  - 從 session_id → principal     │
                  │  - 檢查 role / scopes            │
                  │  - 用 tenant_id 鎖定資料範圍     │
                  │  - 執行 → 回結果                 │
                  └──────────────┬──────────────────┘
                                 │
                  ┌──────────────┴──────────────────┐
                  │ 後端：sqlgate / customerlist /    │
                  │ chat log / quote API / ...        │
                  └─────────────────────────────────┘
```

---

## 4. Principal Schema 規格

### 4.1 完整欄位定義

| 欄位 | 型別 | 必填 | 用途 | 範例 |
|---|---|---|---|---|
| `role` | str | ✓ | RBAC 主鍵；查 POLICY 表決定能用哪些 tool | `owner` / `staff` / `vip_customer` / `basic_customer` / `anon` |
| `tenant_id` | str | ✓ | 多租戶隔離；tool 用來鎖定資料範圍 | `cwsoft` / `前進通訊` / `null`(anon) |
| `db_name` | str | ⚪ | 對應後端 SQL Server DB 名 | `POSConfig` / `Customer_QianJin` |
| `scopes` | list[str] | ⚪ | 細粒度子權限 | `["own_orders", "own_invoices"]` |
| `line_user_id` | str | ⚪ | LINE 來源辨識 | `U34e144c9bf7d30bc07c543a4ebae0df1` |
| `session_id` | str | ✓ | codex session id；MCP server 端 keyed by 此 | `019e2c43-...-d592` |
| `displayed_name` | str | ⚪ | 給 codex 對話時稱呼用 | `colombo` / `前進老闆` |
| `extra` | dict | ⚪ | 個別 AI 場景的特殊欄位 | `{"vip_tier": "gold"}` |

### 4.2 預設 role 表

| role | 描述 | 對應典型對象 |
|---|---|---|
| `owner` | cwsoft 老闆、能做任何事 | colombo |
| `staff` | cwsoft 員工 | 彥偉 / 羿宏 / 士豪 |
| `vip_customer` | 升級方案客戶 | 升級的客戶老闆 |
| `basic_customer` | 標準方案客戶 | 一般客戶老闆 |
| `anon` | 沒綁定身份 | 陌生人 / 未登入 |

---

## 5. Tool 設計守則（重要）

### 5.1 三條鐵律

1. **「能不能用」由 principal.role/scopes 決定**——查 POLICY 表
2. **「能看誰的」由 principal.tenant_id/db_name 鎖定**——**從 principal 取，不接 caller 帶**
3. **「具體查什麼」由 caller 函式參數決定**——caller 只能在自己被授權的範圍內細查

### 5.2 ✗ 危險寫法 vs ✓ 安全寫法

```python
# ✗ 危險：tool 接 db_name 當參數、caller 可亂指定別人的 DB
@tool
def query_database(db_name: str, sql: str):
    return run_sql(db_name, sql)
```

→ vip_customer 把 db_name 改成 `Customer_QuanHong` 就偷到別家資料。

```python
# ✓ 安全：tool 從 principal 拿 db_name、caller 只能傳查詢條件
@tool
def get_my_orders(start_date: str = None, end_date: str = None):
    p = current_principal()
    if not _can(p, "get_my_orders"):
        return {"error": "forbidden"}
    db_name = p["db_name"]            # ← 從身份卡拿
    return run_sql(db_name,
        "SELECT * FROM orders WHERE customer_id=? AND date BETWEEN ? AND ?",
        [p["tenant_id"], start_date, end_date])
```

### 5.3 同一動作對不同 role 拆兩個 tool

老闆能查任意客戶 / 客戶只能查自己——拆成兩個 tool、policy 各鎖各的：

```python
@tool
def get_my_orders(...):           # 客戶用
    p = current_principal()
    if "own_orders" not in p["scopes"]: return {"error": "forbidden"}
    return _q_orders(db=p["db_name"], customer=p["tenant_id"], ...)

@tool
def query_any_customer_db(customer_name: str, sql: str):    # 老闆用
    p = current_principal()
    if "all_dbs" not in p["scopes"]: return {"error": "forbidden"}
    db = lookup_customer_db(customer_name)
    return run_sql(db, sql)
```

客戶連 `query_any_customer_db` 這個 tool name 都看不到（透過分 server 策略）或叫了會被回 forbidden（單 server 策略）。

---

## 6. POLICY 表（v1 草案）

```python
# cwsoft_ai_tools/policy.py

POLICY = {
    # ── 基礎讀檔類 ──────
    "list_project_files":       {"owner", "staff"},
    "read_project_doc":         {"owner", "staff"},

    # ── 客戶查詢類 ──────
    "search_customer":          {"owner", "staff"},
    "get_my_orders":            {"owner", "staff", "vip_customer", "basic_customer"},
    "get_my_invoices":          {"owner", "staff", "vip_customer"},      # basic 看不到發票
    "get_my_chat_history":      {"owner", "staff", "vip_customer"},
    "query_any_customer_db":    {"owner"},                                # 只老闆能跨客戶

    # ── 客戶寫入類 ──────
    "modify_customer_basic":    {"owner", "staff"},
    "promote_customer_tier":    {"owner"},                                # 升等只老闆
    "send_promo_message":       {"owner"},

    # ── 系統 / 維運類 ──────
    "view_chat_log_all":        {"owner"},
    "view_my_chat_log":         {"vip_customer", "basic_customer"},
    "view_oa_settings":         {"owner", "staff"},
    "modify_oa_settings":       {"owner"},

    # ── 公開資訊類 ──────
    "faq_lookup":               {"owner", "staff", "vip_customer", "basic_customer", "anon"},
    "store_hours":              {"owner", "staff", "vip_customer", "basic_customer", "anon"},
}

def can(principal: dict, tool: str) -> bool:
    return principal.get("role") in POLICY.get(tool, set())
```

---

## 7. current_principal() 在 MCP server 端怎麼運作

MCP server 是長住程序、同時可能服務多個 codex session（每個 session 對應一個 LINE 對象）。

### 7.1 內部狀態

```python
# 全域 dict（server 自己維護），用 session_id 當 key
_session_principals: dict[str, dict] = {}

@tool
def setup_context(role: str, tenant_id: str, db_name: str = "",
                  scopes: list[str] = None, line_user_id: str = ""):
    """gtb_codex.py 在每個 LINE 訊息進入 codex 之前、要求 codex 第一件事呼叫這個 tool 來載入身份。"""
    sid = _current_session_id()       # MCP SDK 提供 request context
    _session_principals[sid] = {
        "role":         role,
        "tenant_id":    tenant_id,
        "db_name":      db_name,
        "scopes":       scopes or [],
        "line_user_id": line_user_id,
        "session_id":   sid,
    }
    return {"ok": True, "loaded_role": role}

def current_principal() -> dict | None:
    sid = _current_session_id()
    return _session_principals.get(sid)
```

### 7.2 兩種 session_id 來源

`_current_session_id()` 從哪來——MCP SDK 提供 request context。對 stdio MCP（codex 的場景），
一個連線 = 一個 codex session、SDK 會給穩定的 context id。

如果未來支援 SSE / HTTP MCP（多客戶端共用 server）、要從 HTTP header 帶 session_id 過來。

---

## 8. gtb_codex.py 端的 setup 流程

每個 LINE 訊息進來：

```python
def callback(oaid, event):
    user_text    = event.message.text
    line_user_id = event.source.user_id

    # 1. 從 line_user_id 查 principal
    principal = lookup_principal(line_user_id)   # 從 principals.json / DB

    # 2. 構造一段 system-style 前置指令給 codex、要它先呼叫 setup_context
    setup_instr = (
        f"[SYSTEM] 在回答以下使用者訊息之前、請先呼叫 setup_context tool 並帶入這些參數："
        f"\n  role='{principal['role']}',"
        f"\n  tenant_id='{principal['tenant_id']}',"
        f"\n  db_name='{principal.get('db_name','')}',"
        f"\n  scopes={principal.get('scopes',[])},"
        f"\n  line_user_id='{line_user_id}'"
        f"\n[USER] {user_text}"
    )

    reply = codex_resume(SESSION_ID, setup_instr)
    line_reply(reply)
```

### 8.1 principals.json（v1 簡版）

```json
{
  "U34e144c9bf7d30bc07c543a4ebae0df1": {
    "role": "owner",
    "tenant_id": "cwsoft",
    "db_name": "POSConfig",
    "scopes": ["all_dbs", "all_chats", "modify_customer", "promote_customer_tier"]
  },
  "U99xy_客戶A_的 line user id": {
    "role": "vip_customer",
    "tenant_id": "前進通訊",
    "db_name": "Customer_QianJin",
    "scopes": ["own_orders", "own_invoices"]
  }
}
```

未來成熟可改成 SQLite 表 + 跟 cwsoft accountSystemServer 串。

---

## 9. 多 server vs 單 server：硬隔離 vs 軟檢查

| 策略 | codex 看得到 forbidden tool 的 schema 嗎？ |
|---|---|
| **單 server + tool 內 policy 檢查**（B） | 看得到、叫了被拒 |
| **不同 role 載不同 server**（A） | 看不到、根本不知道存在 |

對「敏感 / 風險高」的 tool（改資料、退款、發促銷），**建議走 A 策略**——掛在 `cwsoft_ai_tools_admin` server、客戶 codex session 的 config.toml 不要載這個 server。codex 連 tool name 都不知道。

對「普通讀類」tool 走 B 策略——掛在 `cwsoft_ai_tools` 通用 server、tool 內檢查、被拒就回 forbidden。codex 會解釋給客戶聽、不洩漏架構也沒大事。

實際 config.toml 大概這樣：

```toml
# 客戶用的 codex 啟動時
[mcp_servers.cwsoft_tools]
command = "python"
args    = ["-m", "cwsoft_ai_tools.server"]

# 阿全經理（老闆）的 codex 啟動時加掛
[mcp_servers.cwsoft_tools_admin]
command = "python"
args    = ["-m", "cwsoft_ai_tools_admin.server"]
```

兩個 server 用的 `cwsoft_ai_tools` 套件是同一份；admin server 多 expose 一些敏感 tool。

---

## 10. 實作路徑（建議順序）

1. **MVP MCP server**（30-50 行 Python + `mcp` SDK）
   - 暴露 1-2 個工具（`list_project_files`、`read_doc`）
   - 註冊進 codex `config.toml`
   - 跑 `codex exec --skip-git-repo-check "list project files"` 驗證能 discover + call

2. **Principal schema v1**
   - `principals.json` 寫入 colombo 自己 + 一個假 vip_customer
   - 加 `lookup_principal(line_user_id)` 函式

3. **setup_context tool + policy.py**
   - server 端 `_session_principals` dict + `setup_context` + `current_principal`
   - `policy.py` 寫前面那張 POLICY 表
   - tool 全部加 `if not can(p, "..."): return forbidden` 開頭

4. **gtb_codex.py 整合**
   - LINE 訊息進來、查 principal、組 setup 指令、塞給 codex
   - 驗證：colombo 能用全部 tool、假客戶用 vip 試 setup_context 後拿到不同 tool 結果

5. **真實客戶資料的 tool**（`get_my_orders` 等）
   - 接 sqlgate
   - 嚴格遵守「db_name 從 principal 拿」的鐵律

6. **客服 AI 起雛形**
   - 寫 `cs_codex.py`（gtb_codex.py 的 fork、針對 customer-facing 場景）
   - 接客服 OA 的 LINE webhook
   - principals.json 加客戶 line_user_id mapping

7. **多 server 拆分（敏感工具搬出去）**
   - 建 `cwsoft_ai_tools_admin` server
   - 客戶用的 codex config 不掛這個 server
   - 老闆 / 員工 codex config 掛上

---

## 11. 待解 / 風險

- **codex 會乖乖呼叫 setup_context 嗎？**——靠 prompt 強約束，但不是 100% 保證。最壞情境：principal 沒 set、`current_principal()` 回 None、所有 tool 都拒。需要在 server 端設這條 fallback。
- **codex on Windows shell DLL bug**——這套 capability-restricted 設計剛好繞過 shell 問題（codex 完全不需要 shell），是 silver lining。
- **session 之間身份 leak 風險**——`_session_principals` dict 用 session_id 區隔，理論上不會。但 MCP stdio 重啟、session_id 重複的可能性要排除。
- **scopes 細到什麼程度才合理**——一開始粗一點（5-8 個 scope 就好），用到痛點才加細。
- **客戶端 LINE user_id 跟「客戶 owner 帳號」的對應**——需要客戶在 LINE 上「綁定」一次，這流程 cwsoft accountSystemServer 應該已經有。要對接。

---

## 12. 一句話總結

> 一個 codex 引擎、一份 MCP 工具集、一張 principal 身份卡——
> 老闆進來看到全部、客戶進來只看到自己的、陌生人只能 FAQ。
> 不必為每種對象訓練不同模型、也不必為每種對象 fork 一份程式。
