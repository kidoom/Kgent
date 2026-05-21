## 4. 模块划分

建议目录（2026-05 包结构重构后）：

```text
Kgent/
  backend/
    app/
      main.py                 # FastAPI 入口
      model_client.py         # 模型层 public API（re-export app.model.*）
      debug_cli.py            # CLI 兼容入口 → app.cli.debug
      api/
        chat.py               # POST /api/chat
      cli/
        debug.py              # Debug REPL 实现
      core/
        config.py             # KGENT_* 环境变量
      memory/
        session_store.py      # 进程内短期 session（V0.1.1）
      model/
        base.py               # ModelClient 协议 + provider registry
        heuristic.py          # 离线 deterministic 模型
        openai.py             # OpenAI-compatible 客户端
      runtime/
        loop.py               # model-tool-model loop controller
        messages.py           # Message / AgentStep 协议
        prompts.py            # SYSTEM_PROMPT / PLAN_TURN_USER_PROMPT
        permissions.py        # 工具权限策略（V0.2）
      tools/
        base.py
        registry.py
        calculator.py
        read_file.py
        list_files.py
    pyproject.toml
  frontend/
    README.md
  tests/
  scripts/
```

模块职责：

| 模块 | 职责 |
| --- | --- |
| `main.py` | FastAPI 应用入口、`GET /health`、lifespan |
| `api/chat.py` | HTTP 接口，接收前端请求 |
| `runtime/loop.py` | 控制 model-tool-model 循环（CC 四相 steps） |
| `runtime/messages.py` | message / tool_use / tool_result / AgentStep |
| `runtime/prompts.py` | system prompt 与 debug plan prompt |
| `runtime/permissions.py` | 工具权限策略（V0.2） |
| `memory/session_store.py` | 进程内短期 session（V0.1.1） |
| `model/*` + `model_client.py` | 可插拔模型 provider |
| `tools/base.py` | Tool 协议与 schema 投影 |
| `tools/registry.py` | 注册工具并提供 `find_tool_by_name()` |
| `tools/*.py` | 具体工具实现 |
| `core/config.py` | 环境变量和运行配置 |
| `cli/debug.py` | 终端可观测 debug REPL（V0.1.4） |

> 新代码应使用 `app.runtime.*`、`app.memory.*`、`app.model.*`、`app.cli.*` 导入。旧 `app.agent.*` 兼容层已移除。
