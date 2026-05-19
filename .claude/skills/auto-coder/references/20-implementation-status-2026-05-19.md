## 20. Implementation Status - 2026-05-19

This section records what the current Kgent repository has implemented.

### 20.1 Current File Layout

```text
backend/app/
  main.py
  api/
    chat.py
  agent/
    loop.py
    messages.py
    session_store.py
    model_client.py
    prompts.py
    model/
      __init__.py
      base.py
      heuristic.py
      openai.py
  tools/
    base.py
    registry.py
    calculator.py
    list_files.py
    read_file.py
  core/
    config.py
  debug_cli.py

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
```

### 20.2 Implemented Backend Capabilities

- [x] FastAPI app entrypoint in `backend/app/main.py`.
- [x] Health endpoint: `GET /health`（含 `provider`、`available_providers`、`model_client_ready`）。
- [x] Chat endpoint: `POST /api/chat`.
- [x] Pydantic request/response models for chat API.
- [x] Minimal model-tool-model loop in `agent/loop.py`.
- [x] Message protocol models in `agent/messages.py`.
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
- [x] System prompt aligned with multi-turn session and tool loop (`agent/prompts.py`).
- [x] Debug CLI prints THINK/CALL/OBSERVE/FINAL via shared `run_agent()`.
- [x] In-memory short-term session store (`session_id` -> `messages[]`).
- [x] `session_id` on `POST /api/chat` request and response.
- [x] Multi-turn context within the same session (including prior tool results).
- [x] Debug CLI interactive mode reuses the same session.
- [x] Session message cap via `KGENT_MAX_SESSION_MESSAGES` and `trim_session_messages()`.
- [x] FastAPI lifespan reuses model client (`app.state.model_client`).

### 20.3 Implemented Model Layer

- [x] `ModelClientProtocol` boundary.
- [x] `ModelClientError` for provider/network/parse failures.
- [x] Pluggable model client registry with `register_model_client()`.
- [x] Backward-compatible `agent/model_client.py` re-export module.
- [x] Offline deterministic `heuristic` model client.
- [x] OpenAI-compatible model client using Chat Completions and tool calls.
- [x] OpenAI-compatible message/tool conversion helpers.
- [x] Invalid model tool-call JSON is wrapped as `ModelClientError`.
- [x] API maps `ModelClientError` to HTTP 502.

### 20.4 Implemented Configuration

- [x] Runtime settings live in `core/config.py`.
- [x] Configuration source order is:

```text
environment variables -> .env -> built-in defaults
```

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
```

- [x] `.env` is parsed without mutating `os.environ`.
- [x] `settings.json` is no longer part of the configuration path.
- [x] `.env.example` documents the supported variables.
- [x] CORS origins are configurable via `KGENT_CORS_ORIGINS`.
- [x] File tools block hidden paths such as `.env` and `.git/config`.

### 20.5 Implemented Tests

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

Current test command:

```bash
.venv\Scripts\python.exe -m pytest -q
```

Current result:

```text
22 passed
```

### 20.6 Still Not Implemented

These remain out of scope for the current V0.1 implementation:

- [ ] Real frontend UI beyond `frontend/README.md`.
- [ ] Streaming model output.
- [ ] Streaming tool execution.
- [ ] Tool permission approval flow.
- [ ] Safe/unsafe tool risk categories.
- [ ] Parallel tool execution.
- [ ] Dynamic tool loading.
- [ ] MCP integration.
- [ ] Context compression.
- [ ] Long-term memory.
- [ ] User authentication.

### 20.7 Current Known Risks

- `KGENT_PROVIDER` is free-form; invalid provider may only surface at startup (`model_client_ready: false`) or request time (HTTP 502).
- Session store is in-process only; restarting the server clears all sessions; multi-worker deployments do not share sessions.
- Session trim drops middle history (keeps system + tail); not a substitute for V0.5 context compression.
- Canonical spec path: repo `.spec-source` → `D:\claude-code\spec\mini-agent-v0.1\DEV_spec.md` (Kgent 仓库内不再维护副本 `DEV_SPEC.md`).

一句话总结：

```text
V0.1 要证明：只要有 messages、tools schema、runtime、loop controller，
我们就已经拥有了一个最小 agent。
```
