## 19. 当前实现状态

This section records what the current Kgent repository has implemented.

### 19.1 Current File Layout

```text
backend/app/
  main.py                   # FastAPI entry + GET /health
  api/
    sessions.py             # POST messages / permission / cancel
    events.py               # GET SSE event stream
    runtime_service.py      # background run execution
    deps.py, schemas.py, errors.py
  model_client.py
  debug_cli.py
  cli/debug.py
  core/config.py
  memory/session_store.py
  model/base.py, openai.py
  runtime/loop.py, messages.py, prompts.py, permissions.py, protocol.py, host.py, run_manager.py
  tools/

frontend/src/               # Vite + React (useRuntimeHttp, runtimeClient.ts)
docs/API.md                 # HTTP + SSE API 文档
scripts/run_server.py       # optional uvicorn launcher (.env + TLS)
notebooks/                  # Jupyter walkthrough

tests/
  fake_model.py             # offline FakeModelClient (provider "fake")
  test_http_runtime.py      # HTTP + SSE integration
  test_run_manager.py
  test_runtime_protocol.py
  ...
```

### 19.2 Implemented Backend Capabilities

- [x] FastAPI HTTP + SSE runtime (`uvicorn app.main:app` or `scripts/run_server.py`).
- [x] Health probe: `GET /health`.
- [x] HTTP commands: send message / permission / cancel; SSE pushes `AgentEvent`.
- [x] Minimal model-tool-model loop in `runtime/loop.py`.
- [x] Message / Tool / AgentStep 协议。
- [x] Built-in tools: calculator, list_files, read_file。
- [x] CC-style step trace: `think` / `call` / `observe` / `final`。
- [x] In-memory session store（`session_id` → `messages[]`）。
- [x] Debug CLI（`CLIHost` + checkpoint trace）。
- [x] Permission policies + `AskPolicy`（HTTP interactive + SSE）。
- [x] `run_agent_stream()` + `loop_checkpoint`（含 `tool_schemas`）。
- [x] OpenAI-compatible model client（DeepSeek 等）。
- [x] **V0.2.3** 已移除 legacy WebSocket transport（`transport/ws_server.py`）。

### 19.3 Implemented Model Layer

- [x] `ModelClientProtocol` boundary.
- [x] `ModelClientError` for provider/network/parse failures.
- [x] Pluggable model client registry with `register_model_client()`.
- [x] Top-level `model_client.py` re-export module for `app.model.*`.
- [x] OpenAI-compatible model client using Chat Completions and tool calls.
- [x] Default provider: `openai`（DeepSeek via `KGENT_BASE_URL`）。
- [x] pytest offline client: `tests/fake_model.py`（registry name `fake`，非生产）。
- [x] OpenAI-compatible message/tool conversion helpers.
- [x] OpenAI client：`tools=[]` 时不传 tools；同时保留 `content` + `tool_calls`。
- [x] `Message.assistant_text` 用于带 tool 的 assistant 可见计划回放。
- [x] Invalid model tool-call JSON is wrapped as `ModelClientError`.
- [x] HTTP run maps `ModelClientError` to `error` / `run_failed` SSE events.

### 19.4 Implemented Configuration

- [x] Runtime settings live in `core/config.py`.
- [x] Configuration source order（`get_settings()`，API / 默认）:

```text
environment variables -> .env -> built-in defaults
```

- [x] Debug CLI 使用 `get_dotenv_settings()`（**.env 优先于环境变量**，便于本地填 `KGENT_API_KEY` 调试）。

- [x] Supported variables:

```text
KGENT_PROVIDER
KGENT_MODEL
KGENT_API_KEY
KGENT_BASE_URL
KGENT_MAX_STEPS
KGENT_PROJECT_ROOT
KGENT_MAX_SESSION_MESSAGES
KGENT_PERMISSION_MODE
KGENT_CORS_ORIGINS
KGENT_SESSION_EVENT_MAX
KGENT_HOST / KGENT_PORT / KGENT_RELOAD   # scripts/run_server.py
KGENT_SSL_KEYFILE / KGENT_SSL_CERTFILE   # scripts/run_server.py
VITE_API_BASE / VITE_SESSION_ID          # frontend
```

- [x] `.env` is parsed without mutating `os.environ`.
- [x] `get_dotenv_settings()` for debug CLI（.env 优先）；`get_settings()` for API（env 优先）。
- [x] `settings.json` is no longer part of the configuration path.
- [x] `.env.example` documents the supported variables.
- [x] CORS origins are configurable via `KGENT_CORS_ORIGINS`.
- [x] File tools block hidden paths such as `.env` and `.git/config`.

### 19.5 Implemented Tests

- [x] Tool unit tests for calculator and read-file path traversal.
- [x] Agent-loop tests for calculator and read-file flows.
- [x] HTTP + SSE runtime tests（`test_http_runtime.py`）。
- [x] pytest pins `KGENT_PROVIDER=fake` via `tests/conftest.py`。
- [x] Short-term session memory tests (`tests/test_session_memory.py`, 4 cases).
- [x] Per-test session isolation via `tests/conftest.py` (`reset_sessions()`).
- [x] Debug CLI smoke test (`tests/test_debug_cli.py`).
- [x] AgentStep validation tests (`tests/test_agent_step.py`).
- [x] Session trim tests (`tests/test_session_trim.py`).
- [x] Health endpoint lists registered providers.
- [x] Permission layer tests (`tests/test_permissions.py`, 15+ cases).
- [x] **V0.2.1** Runtime protocol tests (`tests/test_runtime_protocol.py`).
- [x] **V0.2.1** RunManager tests (`tests/test_run_manager.py`).

Current test command:

```bash
.venv\Scripts\python.exe -m pytest -q
```

### 19.6 Still Not Implemented

- [ ] Electron 桌面打包（Web 客户端优先）。
- [ ] **Token-level** streaming model output（V0.8）。
- [x] HTTP/SSE runtime approval flow（V0.2.2+）。
- [x] Vite React Web UI（V0.2.2）。
- [ ] HTTP/SSE 鉴权（session 目前仅 id 门禁）。
- [ ] Parallel tool execution.
- [ ] Dynamic tool loading.
- [ ] MCP integration.
- [ ] Context compression.
- [ ] Long-term memory.
- [ ] User authentication.

### 19.7 Current Known Risks

- `KGENT_PROVIDER` invalid → startup `model_client_ready: false` or run-time `error` event.
- Run state 与 session 均仅进程内存；多 worker 不共享；run 无 TTL 清理。
- SSE/HTTP 无鉴权：知道 session_id 的客户端可订阅同一事件流。
- Debug `plan_before_act` doubles model calls per turn (cost/latency); not enabled on API.
- Session trim drops middle history (keeps system + tail); not a substitute for V0.5 context compression.
- Canonical spec path: repo `.spec-source` → `D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md` (Kgent 仓库内 chapter 文件为 sync 副本，本地已按 V0.2.2 HTTP+SSE 更新)。

一句话总结：

```text
V0.1 要证明：只要有 messages、tools schema、runtime、loop controller，
我们就已经拥有了一个最小 agent。
```

---
