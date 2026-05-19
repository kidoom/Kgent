## 16. 工程加固与 Prompt 对齐（V0.1.3）

> **版本状态：已完成（2026-05-19）** — P0/P1 项已落地 Kgent 仓库。

### 16.1 目标

让 **system prompt、loop 行为、session 边界、API 可观测性** 与 V0.1.1 / V0.1.2 的实现一致，并消除已知工程风险。

### 16.2 P0：Prompt 与 loop 对齐

| ID | 任务 | 状态 | 说明 |
| --- | --- | --- | --- |
| P0-1 | 更新 `SYSTEM_PROMPT` | [x] | `backend/app/agent/prompts.py` |
| P0-2 | 删除未使用的 `infer_project_root()` | [x] | `backend/app/agent/loop.py` |

**Prompt 记录要点（`prompts.py`）：**

- 同 session 内会看到历史 user / assistant / tool_result，需接着上文回答。
- 工作循环：读上下文 → 判断是否调工具 → 用 observation 继续或收尾。
- 调工具前用简短可见文字说明意图（对齐 `think` step）。
- tool_result 是外部观察，禁止编造；错误时依据 observation 修正或说明阻塞。
- 不把隐藏 chain-of-thought 写入协议；仅可见文本进入 `think`。

### 16.3 P1：运行时加固

| ID | 任务 | 状态 | 实现位置 |
| --- | --- | --- | --- |
| P1-1 | FastAPI `lifespan` 复用 model client | [x] | `backend/app/main.py`, `api/chat.py` |
| P1-2 | `AgentStep` 按 `type` 字段校验 | [x] | `backend/app/agent/messages.py` |
| P1-3 | Session 消息数上限与截断 | [x] | `session_store.py`, `loop.py`, `core/config.py` |

**P1-1 lifespan：**

- 启动时 `build_model_client()` 挂到 `app.state.model_client`，关闭应用时 `close()`。
- `POST /api/chat` 优先复用共享 client；无共享实例时再按请求创建（测试 / 启动失败降级）。

**P1-2 校验规则：**

- `think`：非空 `content`
- `final`：必须有 `content`（可为空字符串）
- `call`：`tool_use_id`、`tool_name`、`tool_input`
- `observe`：`tool_use_id`、`tool_name`、`content`

**P1-3 session 截断：**

- 配置项 `KGENT_MAX_SESSION_MESSAGES`（默认 `100`，范围 `4–500`）。
- `trim_session_messages()`：保留 `system` + 最近 tail。
- 在 `run_agent` 中：追加 user 后、每轮 `call_model` 前执行截断。

### 16.4 API / 配置补充

**`GET /health` 响应（已实现）：**

```json
{
  "status": "ok",
  "provider": "heuristic",
  "available_providers": ["heuristic", "openai"],
  "model_client_ready": true
}
```

**新增环境变量：**

```text
KGENT_MAX_SESSION_MESSAGES
```

**`POST /api/chat` 请求/响应（当前）：**

```json
{
  "session_id": "default",
  "message": "继续刚才的话题"
}
```

```json
{
  "session_id": "default",
  "answer": "...",
  "message_count": 6,
  "steps": [
    { "type": "think", "turn_index": 0, "content": "..." },
    { "type": "call", "turn_index": 0, "tool_name": "calculator", "tool_input": {} },
    { "type": "observe", "turn_index": 0, "tool_name": "calculator", "content": "102" },
    { "type": "think", "turn_index": 1, "content": "..." },
    { "type": "final", "turn_index": 1, "content": "..." }
  ]
}
```

> **破坏性变更**：`steps[].type` 不再是 `tool_use` / `tool_result`；前端需按四相渲染。

### 16.5 测试基线（Kgent）

```bash
.venv\Scripts\python.exe -m pytest -q
# 22 passed
```

新增/更新测试文件：

```text
tests/test_agent_step.py      # AgentStep 校验
tests/test_session_trim.py    # session 截断
tests/test_api.py             # health + chat（四相 steps）
```

---
