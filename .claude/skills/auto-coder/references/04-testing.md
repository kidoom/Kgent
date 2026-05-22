## 4. 模块划分

建议目录（2026-05 包结构，V0.2.2 HTTP + SSE）：

```text
Kgent/
  backend/
    app/
      main.py                 # FastAPI entry + GET /health
      api/
        sessions.py           # POST messages / permission / cancel
        events.py             # GET SSE event stream
        runtime_service.py    # background run execution
        deps.py, schemas.py, errors.py
      model_client.py
      debug_cli.py
      cli/debug.py
      core/config.py
      memory/session_store.py
      model/base.py, openai.py
      runtime/loop.py, messages.py, prompts.py, permissions.py, protocol.py, host.py, run_manager.py
      tools/
    pyproject.toml
  frontend/                   # Vite + React (useRuntimeHttp)
  docs/API.md                 # HTTP + SSE API 文档
  notebooks/                  # Jupyter loop walkthrough
  tests/fake_model.py         # pytest 离线 client
  tests/test_http_runtime.py  # HTTP + SSE 集成测试
  scripts/run_server.py       # 可选：从 .env 启动 uvicorn（含 TLS）
```

模块职责：

| 模块 | 职责 |
| --- | --- |
| `main.py` | FastAPI app、CORS、`GET /health` |
| `api/sessions.py` | 发消息、权限决策、取消 run |
| `api/events.py` | session-scoped SSE `AgentEvent` 推送 |
| `api/runtime_service.py` | 后台调度 `run_agent_stream` |
| `runtime/loop.py` | `run_agent_stream()` 核心循环 + `run_agent()` 兼容包装 |
| `runtime/protocol.py` | `AgentEvent`、command 模型、`loop_checkpoint`（含 `tool_schemas`） |
| `runtime/host.py` | `AgentHost` + `CollectingHost` / `CLIHost` / `RunManagerHost` |
| `runtime/run_manager.py` | 进程内 run 监督、pending permission、cancel、session 事件历史 |
| `memory/session_store.py` | 进程内短期 session（V0.1.1） |
| `model/openai.py` | OpenAI-compatible client（DeepSeek 等） |
| `cli/debug.py` | 终端 debug REPL |

> 已移除：`transport/ws_server.py`、`POST /api/chat`（V0.1 同步 JSON）、生产 `heuristic`。导入使用 `app.api.*`、`app.runtime.*`、`app.memory.*`、`app.model.*`、`app.cli.*`。
