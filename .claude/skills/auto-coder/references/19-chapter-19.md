## 19. 当前实现状态

This section records what the current Kgent repository has implemented.

### 19.1 Current File Layout

```text
backend/app/
  main.py
  model_client.py
  debug_cli.py              # thin wrapper → cli/debug.py
  api/
    chat.py
  cli/
    debug.py
  core/
    config.py
  memory/
    session_store.py
  model/
    base.py
    heuristic.py
    openai.py
  runtime/
    loop.py
    messages.py
    prompts.py
    permissions.py
  tools/
    base.py
    registry.py
    calculator.py
    list_files.py
    read_file.py

frontend/
  README.md

tests/
  conftest.py
  test_agent_loop.py
  test_api.py
  test_tools.py
  test_session_memory.py
  test_session_trim.py
  test_agent_step.py
  test_debug_cli.py
  test_permissions.py
```

### 19.2 Implemented Backend Capabilities

- [x] FastAPI app entrypoint in `backend/app/main.py`.
- [x] Health endpoint: `GET /health`（含 `provider`、`available_providers`、`model_client_ready`）。
- [x] Chat endpoint: `POST /api/chat`.
- [x] Pydantic request/response models for chat API.
- [x] Minimal model-tool-model loop in `runtime/loop.py`.
- [x] Message protocol models in `runtime/messages.py`.
- [x] Tool protocol and schema projection in `tools/base.py`.
- [x] Runtime tool registry helpers in `tools/registry.py`.
- [x] Built-in `calculator` tool.
- [x] Built-in `list_files` tool.
- [x] Built-in `read_file` tool.
- [x] Project-root path guard for file tools.
- [x] Tool execution errors are returned as `tool_result` blocks instead of crashing the loop.
- [x] `max_steps` guard in the agent loop.
- [x] CC-style step trace: `think` / `call` / `observe` / `final` with `turn_index`.
- [x] `AgentStep` pydantic validation per step type.
- [x] System prompt aligned with multi-turn session and tool loop (`runtime/prompts.py`).
- [x] Debug CLI：交互 REPL、`--once`、`--compact`、`on_trace` checkpoint（见 §17）。
- [x] `run_agent(..., plan_before_act=True)` 仅 debug CLI 使用；API 为单阶段 loop。
- [x] In-memory short-term session store (`session_id` -> `messages[]`)；无持久化。
- [x] `session_id` on `POST /api/chat` request and response.
- [x] Multi-turn context within the same session (including prior tool results).
- [x] Debug CLI interactive mode reuses the same session.
- [x] Session message cap via `KGENT_MAX_SESSION_MESSAGES` and `trim_session_messages()`.
- [x] FastAPI lifespan reuses model client (`app.state.model_client`).
- [x] Tool `risk_level` metadata (`low` / `medium` / `high`) — runtime-only, not projected to model schema.
- [x] Permission policies in `runtime/permissions.py`: `AllowAllPolicy`, `RiskBasedPolicy`, `InteractivePolicy` (V0.2).
- [x] `run_agent(..., policy=...)` decision point before `execute_tool_use`; deny short-circuits with synthetic `permission_denied` tool_result (V0.2).
- [x] `AgentStep.decision` (`allow` / `deny` / `ask`) on `call` steps (V0.2).
- [x] `after_permission` trace checkpoint emitted only on non-allow decisions (V0.2).
- [x] `KGENT_PERMISSION_MODE` env var (`allow_all` / `risk_based` / `interactive`, default `risk_based`).
- [x] API forcibly downgrades `interactive` to `risk_based` (HTTP cannot block on user prompt).
- [x] Debug CLI `--permission` flag with `[y/N]` stdin asker for medium/high tools.
- [x] `GET /health` exposes `permission_mode`, `effective_permission_mode`, and `tool_risks` map.
- [x] Package layout refactor: `runtime/` + `memory/` + `model/` + `cli/`（移除 `app.agent.*` 兼容层）。

### 19.3 Implemented Model Layer

- [x] `ModelClientProtocol` boundary.
- [x] `ModelClientError` for provider/network/parse failures.
- [x] Pluggable model client registry with `register_model_client()`.
- [x] Top-level `model_client.py` re-export module for `app.model.*`.
- [x] Offline deterministic `heuristic` model client.
- [x] OpenAI-compatible model client using Chat Completions and tool calls.
- [x] OpenAI-compatible message/tool conversion helpers.
- [x] OpenAI client：`tools=[]` 时不传 tools；同时保留 `content` + `tool_calls`。
- [x] `Message.assistant_text` 用于带 tool 的 assistant 可见计划回放。
- [x] Invalid model tool-call JSON is wrapped as `ModelClientError`.
- [x] API maps `ModelClientError` to HTTP 502.

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
KGENT_CORS_ORIGINS
KGENT_MAX_SESSION_MESSAGES
KGENT_PERMISSION_MODE
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
- [x] API test for `/api/chat` calculator flow.
- [x] API test pins `KGENT_PROVIDER=heuristic` so local real-model config does not affect tests.
- [x] Short-term session memory tests (`tests/test_session_memory.py`, 4 cases).
- [x] Per-test session isolation via `tests/conftest.py` (`reset_sessions()`).
- [x] Debug CLI smoke test (`tests/test_debug_cli.py`).
- [x] AgentStep validation tests (`tests/test_agent_step.py`).
- [x] Session trim tests (`tests/test_session_trim.py`).
- [x] Health endpoint lists registered providers.
- [x] Permission layer tests (`tests/test_permissions.py`, 14 cases).

Current test command:

```bash
.venv\Scripts\python.exe -m pytest -q
```

Current result:

```text
41 passed
```

### 19.6 Still Not Implemented

These remain out of scope（详见各版本章节的「不在范围」小节）：

- [ ] Real frontend UI beyond `frontend/README.md`.
- [ ] Streaming model output.
- [ ] Streaming tool execution.
- [ ] HTTP-side asynchronous approval flow (V0.2 implements CLI-only `ask`).
- [ ] Parallel tool execution.
- [ ] Dynamic tool loading.
- [ ] MCP integration.
- [ ] Context compression.
- [ ] Long-term memory.
- [ ] User authentication.

### 19.7 Current Known Risks

- `KGENT_PROVIDER` is free-form; invalid provider may only surface at startup (`model_client_ready: false`) or request time (HTTP 502).
- Session store is in-process only; restarting the server or exiting debug CLI clears sessions; multi-worker deployments do not share sessions.
- Debug `plan_before_act` doubles model calls per turn (cost/latency); not enabled on API.
- Session trim drops middle history (keeps system + tail); not a substitute for V0.5 context compression.
- Canonical spec path: repo `.spec-source` → `D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md` (Kgent 仓库内不再维护副本 `DEV_SPEC.md`).

一句话总结：

```text
V0.1 要证明：只要有 messages、tools schema、runtime、loop controller，
我们就已经拥有了一个最小 agent。
```

---
