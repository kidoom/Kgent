## 17. V0.1.4 — Debug CLI 可观测性

> **版本状态：已完成（2026-05-19）** — 仅 `backend/app/cli/debug.py`；**不改变** `POST /api/chat` 的 loop 语义。

### 17.1 目标

在终端复刻「可观测 agent runtime」，用于学习 CC 范式与排查 loop；**不是**生产聊天产品。

### 17.2 运行方式

```bash
cd backend
python -m app.debug_cli                    # 默认：交互多轮 REPL
python -m app.debug_cli --once "消息"      # 单次
python -m app.debug_cli --compact          # 只打 checkpoint + steps，不 dump 全表 messages
python -m app.debug_cli --provider heuristic
python -m app.debug_cli --fresh-session    # 启动前清空 SESSIONS
```

交互命令：`/help`、`/reset`、`/history`、`exit`/`quit`。

### 17.3 与 API loop 的差异

| 能力 | `POST /api/chat` | Debug CLI |
| --- | --- | --- |
| `plan_before_act` | `False`（默认） | `True` |
| 每轮 API 调用次数 | 1× `call_model`（有工具时） | 2×（plan 无工具 + act 有工具） |
| Trace checkpoint | 无（不传 `on_trace`） | `after_plan` / `after_act` / `after_tool` / … |
| 配置加载 | `get_settings()` env 优先 | `get_dotenv_settings()` .env 优先 |

### 17.4 Session 边界（与 §14 一致）

- 存储：`SESSIONS: dict[str, list[Message]]` 进程内内存（`session_store.py`）。
- 进程结束或 `reset_sessions()` / `/reset` 后丢失；**无磁盘持久化**。
- 默认 `session_id`：`debug-cli`（与 API 默认 `default` 分离，避免混用）。

### 17.5 实现进度表（V0.1.4）

| ID | 任务 | 状态 | 实现位置 | 验证 |
| --- | --- | --- | --- | --- |
| V0.1.4-1 | 交互式多轮 REPL（复用 model client） | [x] | `debug_cli.py` | 手动 / 文档 |
| V0.1.4-2 | `plan_before_act` 仅 debug 开启 | [x] | `loop.py`, `debug_cli.py` | API 测试仍单阶段 |
| V0.1.4-3 | `--compact` trace | [x] | `debug_cli.py` | 手动 |
| V0.1.4-4 | OpenAI 保留 content+tool_calls | [x] | `model/openai.py` | agent loop |
| V0.1.4-5 | `Message.assistant_text` | [x] | `messages.py` | OpenAI 回放 |
| V0.1.4-6 | `PLAN_TURN_USER_PROMPT`（仅 plan 阶段） | [x] | `prompts.py` | debug trace |

### 17.6 仍不在 V0.1.4 范围

- [ ] 流式输出（token 级）
- [ ] SSE / WebSocket 推送到前端
- [ ] Session 持久化（SQLite / 文件）
- [ ] 将 `plan_before_act` 默认开启到 API

---

### 17.7 Debug 专用：plan → act 双阶段（仅 debug CLI）

> **不用于 `POST /api/chat`**。通过 `run_agent(..., plan_before_act=True)` 开启。

每轮 `turn`：

```text
1. Plan  : call_model(tools=[]) + 临时 PLAN_TURN_USER_PROMPT（不写入 session）
          → append assistant 计划文字 → AgentStep(think)
2. Act    : call_model(tools=schemas) → tool_use 或 final
3. Tools  : call → observe（tool_result 写入 messages）→ 下一轮
```

与 Cursor/CC 界面上「先规划再执行」的可见文字类似，但仍是 **API 可见 content**，非推理模型隐藏通道。

---
