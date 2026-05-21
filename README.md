# Kgent

Kgent is a small FastAPI agent runtime built around a Claude Code-style loop:

```text
user input -> model -> tool_use -> runtime -> tool_result -> model -> final answer
```

The current codebase intentionally keeps the runtime simple and observable so it
can be used as a learning project and as a base for future agent features.

## Project Layout

```text
backend/app/
  api/              FastAPI routes and HTTP request handling
  cli/              local debug CLI entrypoints
  core/             environment-based application settings
  memory/           in-process session memory
  model/            model client interface and provider implementations
  runtime/          agent loop, messages, prompts, host IO, and permission checks
  tools/            tool definitions, path safety, and registry
  main.py           FastAPI application entrypoint
  model_client.py   public convenience exports for model clients
  debug_cli.py      legacy CLI wrapper for app.cli.debug

tests/              pytest suite for API, loop, tools, memory, and permissions
frontend/           placeholder for future UI work
scripts/            small project maintenance scripts
```

New code should import from `app.runtime.*`, `app.model.*`, `app.memory.*`,
and `app.cli.*`.

## Run Backend

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --app-dir backend --reload
```

Then send a request:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"calculate 12 * 8 + 6\"}"
```

## Runtime WebSocket (V0.2.1)

For interactive runs that can pause and ask for tool permission approval, connect
to the bidirectional runtime protocol:

```text
WS /api/runtime
```

Client commands:

```json
{ "type": "start_run", "session_id": "default", "message": "read README.md" }
{ "type": "permission_decision", "run_id": "run_x", "permission_request_id": "perm_x", "decision": "allow" }
{ "type": "cancel_run", "run_id": "run_x" }
```

Server events include `run_started`, `agent_step`, `permission_required`,
`permission_resolved`, `run_finished`, `run_cancelled`, and `error`.

`POST /api/chat` remains the synchronous compatibility path. It collects runtime
events internally and returns the same JSON shape as before. HTTP requests never
block waiting for user approval; use the WebSocket runtime for interactive
`ask` flows.

## Model Configuration

Configuration comes from environment variables or `.env`; the old
`settings.json` flow is no longer needed.

Precedence:

```text
environment variables -> .env -> built-in defaults
```

Useful variables:

```text
KGENT_PROVIDER=heuristic
KGENT_MODEL=deepseek-chat
KGENT_API_KEY=your_api_key
KGENT_BASE_URL=https://api.deepseek.com
KGENT_PERMISSION_MODE=risk_based
```

Set `KGENT_PROVIDER=openai` to use an OpenAI-compatible provider. Without an
API key, Kgent defaults to the deterministic local heuristic client so tests
and local development can run offline.

## Debug CLI

Run one request through the observable agent loop:

```bash
python -m app.cli.debug --provider heuristic --once "calculate 12 * 8 + 6"
```

Start an interactive debug session:

```bash
python -m app.cli.debug
```

The legacy `python -m app.debug_cli` entrypoint still works as a compatibility
wrapper. The debug CLI prints messages, model outputs, tool calls, tool
results, permission decisions, and the final answer. It shows observable
runtime events, not hidden model chain-of-thought.

## Tool Permissions

Each tool has a `risk_level` (`low`, `medium`, or `high`). A `PermissionPolicy`
decides whether a `tool_use` may run before the runtime executes it.

```text
KGENT_PERMISSION_MODE=risk_based   # default: low/medium auto-approve, high denied
KGENT_PERMISSION_MODE=allow_all    # legacy behavior
KGENT_PERMISSION_MODE=interactive  # CLI / WebSocket: medium/high require approval
```

The HTTP API downgrades `interactive` to `risk_based` so `POST /api/chat` cannot
block waiting for terminal input. Use `WS /api/runtime` with
`KGENT_PERMISSION_MODE=interactive` for interactive approval flows. When a tool
is denied, the loop feeds a synthetic `tool_result(is_error=True,
content="permission_denied: ...")` back to the model.

## Spec

The canonical development spec currently lives outside this repo:

```text
D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md
```

The path is also recorded in `.spec-source`. If the external spec changes, sync
the local chapter references with:

```bash
python .claude/skills/auto-coder/scripts/sync_spec.py --force
```

## Test

```bash
python -m pytest -q
```
