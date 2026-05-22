# Kgent

Kgent is a small Python agent runtime built around a Claude Code-style loop:

```text
user input -> model -> tool_use -> runtime -> tool_result -> model -> final answer
```

The current codebase intentionally keeps the runtime simple and observable so it
can be used as a learning project and as a base for future agent features.

## Project Layout

```text
backend/app/
  main.py           FastAPI/ASGI entry (HTTP + SSE)
  api/              HTTP command routes + SSE event stream
  cli/              local debug CLI entrypoints
  core/             environment-based application settings
  memory/           in-process session memory
  model/            model client interface and provider implementations
  runtime/          agent loop, messages, prompts, host IO, and permission checks
  tools/            tool definitions, path safety, and registry
  model_client.py   public convenience exports for model clients
  debug_cli.py      legacy CLI wrapper for app.cli.debug

frontend/           Electron desktop client (Vite + React)
tests/              pytest suite for loop, tools, memory, permissions, HTTP runtime
scripts/            small project maintenance scripts
```

## Quick Start (Debug CLI)

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cd backend
python -m app.cli.debug --once "calculate 12 * 8 + 6"
```

## Desktop Client (Electron)

**Terminal 1 — backend**

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Or from repo root (reads `.env`, including optional TLS):

```bash
python scripts/run_server.py
```

**HTTPS（开发/生产任选其一）**

```bash
# 方式 A：scripts/run_server.py（读取 .env 中的 KGENT_SSL_KEYFILE / KGENT_SSL_CERTFILE）
python scripts/run_server.py

# 方式 B：uvicorn 直接 TLS（需证书）
uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile ./certs/key.pem --ssl-certfile ./certs/cert.pem

# 方式 C：生产推荐 —— Caddy / nginx 终止 TLS，反代到本地 HTTP :8000
```

- HTTP API（开发）：`http://127.0.0.1:8000`
- HTTPS API（示例）：`https://127.0.0.1:8443`
- SSE events：`GET /api/sessions/{session_id}/events`
- Health：`GET /health`

Vite dev server 通过 proxy 把 `/api`、`/health` 转发到后端；前端默认**不设置** `VITE_API_BASE`，使用同源相对路径。

**Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

See [`frontend/README.md`](frontend/README.md). For backend-only debugging, use Debug CLI below.

## Debug CLI

```bash
cd backend
python -m app.cli.debug --permission interactive
```

The legacy `python -m app.debug_cli` entrypoint still works.

## Model Configuration

```text
KGENT_PROVIDER=openai
KGENT_MODEL=deepseek-chat
KGENT_API_KEY=your_api_key
KGENT_BASE_URL=https://api.deepseek.com
KGENT_PERMISSION_MODE=risk_based
```

Set `KGENT_PROVIDER=openai` and `KGENT_API_KEY` for DeepSeek or other OpenAI-compatible APIs.

## Tool Permissions

```text
KGENT_PERMISSION_MODE=risk_based   # low/medium auto-approve, high denied
KGENT_PERMISSION_MODE=allow_all
KGENT_PERMISSION_MODE=interactive  # HTTP / CLI: medium/high require approval
```

When a tool is denied, the loop feeds a synthetic `permission_denied` tool_result
back to the model.

## Spec

Canonical development spec (external):

```text
D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md
```

Sync local chapter references:

```bash
python .claude/skills/auto-coder/scripts/sync_spec.py --force
```

## Test

```bash
python -m pytest -q
```
