## 14. V0.1.1 — 短期记忆 Session Store

> **版本状态：V0.1.1 已完成（2026-05-19）** — Kgent 仓库已实现进程内短期 session，14 项 pytest 通过。

当前 V0.1 的伪代码每次请求都会重新创建 `messages`：

```python
messages = [
    Message(role="system", content=SYSTEM_PROMPT),
    Message(role="user", content=user_input),
]
```

这会导致 agent 每次请求都像全新会话一样开始，无法记住上一轮用户说过什么、模型回答过什么、工具观察到了什么。

短期记忆要解决的问题是：

```text
同一个 session 内，多次 /api/chat 请求应该共享同一份 messages history。
```

V0.1.1 先实现最小内存版 session store：

```python
SESSIONS: dict[str, list[Message]] = {}
```

### 14.1 API 变更

`POST /api/chat` 请求增加 `session_id`：

```json
{
  "session_id": "default",
  "message": "继续刚才的话题"
}
```

响应保留原结构，额外返回当前 session 信息：

```json
{
  "session_id": "default",
  "answer": "...",
  "steps": [],
  "message_count": 6
}
```

如果客户端没有传 `session_id`，后端可以先使用 `"default"`，方便本地 demo。

### 14.2 Agent Loop 改造

`run_agent()` 不再每次创建全新 messages，而是按 `session_id` 读取或初始化历史：

```python
async def run_agent(session_id: str, user_input: str) -> AgentResult:
    messages = SESSIONS.setdefault(session_id, [
        Message(role="system", content=SYSTEM_PROMPT),
    ])

    messages.append(Message(role="user", content=user_input))

    for _ in range(MAX_STEPS):
        response = await call_model(
            messages=messages,
            tools=[tool_to_schema(tool) for tool in TOOLS],
        )

        messages.append(response.assistant_message)

        if not response.tool_uses:
            return AgentResult(
                answer=response.text,
                steps=steps,
                session_id=session_id,
                message_count=len(messages),
            )

        for tool_use in response.tool_uses:
            result = await execute_tool_use(tool_use)
            messages.append(Message(
                role="user",
                content=[ToolResultBlock(
                    tool_use_id=tool_use.id,
                    content=result.content,
                    is_error=result.is_error,
                )],
            ))
```

### 14.3 记忆边界

这不是长期 memory，也不是知识图谱，只是当前进程内的短期会话上下文：

```text
短期记忆 = session_id -> messages[]
```

V0.1.1 暂不实现：

- 持久化到数据库或文件
- context compression
- memory 抽取与召回
- 多用户登录隔离
- 会话列表和删除接口

### 14.4 验收场景

场景 1：同一 session 记得上一轮信息。

```text
Request 1:
  session_id = "s1"
  message = "我叫小明"

Request 2:
  session_id = "s1"
  message = "我叫什么？"

Expected:
  answer 能回答“小明”
```

场景 2：不同 session 互相隔离。

```text
Request 1:
  session_id = "s1"
  message = "我喜欢 Python"

Request 2:
  session_id = "s2"
  message = "我喜欢什么语言？"

Expected:
  s2 不应该知道 s1 的 Python 偏好
```

场景 3：工具结果也进入短期上下文。

```text
Request 1:
  session_id = "s1"
  message = "读取 README.md 并总结"

Request 2:
  session_id = "s1"
  message = "刚才那个项目主要是干什么的？"

Expected:
  模型可以基于上一轮 read_file 的 tool_result 回答
```

### 14.5 实现进度表（V0.1.1）

| ID | 任务 | 状态 | 实现位置 | 验证 |
| --- | --- | --- | --- | --- |
| V0.1.1-1 | 进程内 `SESSIONS` 与 `get_or_create_session()` | [x] | `backend/app/memory/session_store.py` | `reset_sessions()` + `tests/conftest.py` |
| V0.1.1-2 | `run_agent(..., session_id)` 复用历史 messages | [x] | `backend/app/runtime/loop.py` | `tests/test_agent_loop.py`（既有用例仍通过） |
| V0.1.1-3 | `AgentResult.session_id` / `message_count` | [x] | `backend/app/runtime/messages.py` | `tests/test_session_memory.py` |
| V0.1.1-4 | `POST /api/chat` 请求/响应 `session_id` | [x] | `backend/app/api/chat.py` | `test_chat_api_session_fields` |
| V0.1.1-5 | 验收场景 1：同 session 记住姓名 | [x] | `heuristic` 会话召回 + session store | `test_same_session_remembers_name` |
| V0.1.1-6 | 验收场景 2：不同 session 隔离 | [x] | session store 按 key 隔离 | `test_different_sessions_are_isolated` |
| V0.1.1-7 | 验收场景 3：tool_result 进入后续轮次 | [x] | messages 历史保留 tool_result | `test_tool_results_persist_in_session` |
| V0.1.1-8 | debug_cli 交互模式复用 session | [x] | `backend/app/cli/debug.py`（`--session-id`、`/reset`） | `tests/test_debug_cli.py` |

**未纳入 V0.1.1（见 §14.3）**

| ID | 任务 | 状态 |
| --- | --- | --- |
| V0.1.1-N1 | 持久化到数据库或文件 | [ ] |
| V0.1.1-N2 | context compression | [ ] |
| V0.1.1-N3 | memory 抽取与召回 | [ ] |
| V0.1.1-N4 | 多用户登录隔离 | [ ] |
| V0.1.1-N5 | 会话列表和删除 HTTP 接口 | [ ] |

**当前测试结果（Kgent）**

```bash
.venv\Scripts\python.exe -m pytest -q
# 41 passed（含 V0.2）
```
