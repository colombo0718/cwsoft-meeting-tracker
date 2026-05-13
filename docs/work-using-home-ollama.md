# 給 work 端 Claude Code：怎麼用 home 的 Ollama

你目前跑在 work 機器（DESKTOP-P5EBFBE、CPU 機、無 GPU）。
若任務需要 LLM 推理但不想花 Anthropic / OpenAI 的 API token、
home 機器（DESKTOP-J17AJFD、RTX 2060 6GB）上跑著 Ollama 服務、可以呼叫。

---

## 連線方式

`ssh home "<命令>"` ——`home` 別名已設在 `C:\Users\pos\.ssh\config`、透過 Tailscale 私網直連、ed25519 key 認證、無需密碼。

驗證連線：
```bash
ssh home "hostname"
# 應該看到：DESKTOP-J17AJFD
```

---

## Ollama 已下載的模型

| 模型 | 規模 | 用途建議 |
|------|------|----------|
| `gemma3:4b` | 4.3B | **預設選這個**：一般對話、翻譯、潤稿，速度品質平衡 |
| `qwen2.5:7b` | 7.6B | 中文較強、複雜任務、稍慢 |
| `qwen3.5:2b` | 2.3B | 超快、輕量、適合大量短任務 |
| `gsxr/one:latest` | 7.6B | colombo 的自定義模型 |

---

## 呼叫方式

### 一次性生成（最常用）
```bash
ssh home 'curl -s http://localhost:11434/api/generate -d "{\"model\":\"gemma3:4b\",\"prompt\":\"你的提示\",\"stream\":false}"'
```

回傳 JSON、`response` 欄位是生成內容。

### 對話模式（多輪 / 含 system prompt）
```bash
ssh home 'curl -s http://localhost:11434/api/chat -d "{\"model\":\"gemma3:4b\",\"messages\":[{\"role\":\"system\",\"content\":\"你是助手\"},{\"role\":\"user\",\"content\":\"hi\"}],\"stream\":false}"'
```

### 列模型清單
```bash
ssh home "curl -s http://localhost:11434/api/tags"
```

---

## 效能參考

- **冷啟動**：~16 秒（模型第一次載入 VRAM）
- **熱啟動**：~0.2 秒（連續呼叫時模型保持 cached）
- **生成速度**：4B 模型 ~70 tokens/sec、7B 模型 ~30-40 tokens/sec
- **連續呼叫**：保持 model 不換、能維持熱啟動速度

---

## 適合送 Ollama 的任務

✓ 批量翻譯、潤稿、改寫
✓ 短文初稿（標題、摘要、社群貼文）
✓ POS 知識卡的自動分類 / 標籤化
✓ 客戶問題的初步分類（不對外回覆、只內部 routing）
✓ 反正「想多跑幾次也不心痛」的活兒

## 不適合送 Ollama 的任務

✗ 複雜推理、長 context 分析 → 用 Claude Code 本身
✗ 需要 web search 或 tool use → 用 Claude / Gemini
✗ 對「品質下限」有硬要求的客戶面回應 → 7B 模型不夠保險
✗ 對外公開回覆（cwsoft 客服正式回應）→ 還是走 Claude

---

## 故障排查

```bash
# 連不上 home？檢查 Tailscale
ssh home "tailscale status" 2>&1 | head -3

# Ollama 服務沒回應？檢查進程
ssh home "tasklist | findstr ollama"

# 推理太慢？檢查 GPU 是否在用
ssh home "nvidia-smi"
```

home 主機**不是 24/7 跑**——colombo 偶爾會關機。連不上可能就是關機了、不用緊張。

---

## 安全 / 邊界

- ssh home 連線是內網 + key 認證、不對外暴露
- Ollama API 只 listen localhost、外部打不到（要透過 ssh）
- **不要**把 ollama 端點對外公開（沒做 auth、會被白嫖）
- 送進 ollama 的 prompt 留在 home 本機、不外洩

---

## 一句話總結

> work 上需要 LLM 但不想花 API token 時、`ssh home` 進去用 ollama。
> 預設 gemma3:4b，快又夠用；要中文細膩用 qwen2.5:7b；超短任務用 qwen3.5:2b。
