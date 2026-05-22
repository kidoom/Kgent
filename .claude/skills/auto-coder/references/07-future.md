## 7. Runtime Transport 设计

V0.2.2 起传输层为 **FastAPI HTTP + SSE** + Debug CLI；前端通过 HTTP 发命令、SSE 收事件。

完整 API 见仓库 `docs/API.md`。

### 7.1 启动与 `GET /health`

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

或从仓库根目录（读取 `.env`，含可选 TLS）：

```bash
python scripts/run_server.py
```

- HTTP API：`http://127.0.0.1:8000`
- Health：`GET /health`
- SSE：`GET /api/sessions/{session_id}/events`

```json
{
  "status": "ok",
  "provider": "openai",
  "available_providers": ["openai"],
  "model_client_ready": true,
  "permission_mode": "risk_based",
  "effective_permission_mode": "risk_based",
  "tool_risks": {
    "calculator": "low",
    "list_files": "low",
    "read_file": "medium"
  }
}
```

### 7.2 HTTP + SSE 协议

交互式 runtime：**HTTP POST 发命令（立即返回）**，**SSE 推送步骤级事件**（非 token 流式）。

**客户端 → 服务端（HTTP JSON）：**

```text
POST /api/sessions/{session_id}/messages     { "message": "..." }
POST /api/runs/{run_id}/permission           { "permission_request_id", "decision" }
POST /api/runs/{run_id}/cancel               {}
POST /api/sessions                           {}  → 可选，分配随机 session_id
```

**服务端 → 客户端（SSE `agent_event`）：**

```json
{ "type": "run_started", "run_id": "run_x", "session_id": "sess_x", "seq": 1, "payload": {} }
{ "type": "loop_checkpoint", "payload": { "checkpoint": "before_model_call", "messages": [], "tool_schemas": [] } }
{ "type": "agent_step", "payload": { "step": { "type": "call", "tool_name": "read_file" } } }
{ "type": "permission_required", "payload": { "permission_request": { "tool_name": "read_file", "risk_level": "medium" } } }
{ "type": "run_finished", "payload": { "answer": "...", "message_count": 12, "steps": [] } }
```

`loop_checkpoint` 在 `before_model_call` 时携带完整 `messages` + `tool_schemas`，供前端 / Notebook 展示 LLM 请求拼装。

SSE 支持 `from_seq` / `Last-Event-ID` 断线重连重放；session 历史条数由 `KGENT_SESSION_EVENT_MAX` 控制。

### 7.3 前端 session 与安全（V0.2.2）

- 默认：`POST /api/sessions` 分配随机 id，持久化到 `localStorage`
- 可选：`VITE_SESSION_ID` 固定 session（单人调试）
- **已知边界**：SSE/HTTP 目前无鉴权，仅以 session_id 区分；生产需后续加 token

### 7.4 已移除的传输（历史）

| 移除项 | 时期 | 替代 |
| --- | --- | --- |
| `POST /api/chat` 同步 JSON | V0.1 | HTTP + SSE |
| `transport/ws_server.py` WebSocket | V0.2.1～V0.2.2 过渡 | `api/sessions.py` + `api/events.py` |
| `websockets` Python 依赖 | V0.2.3 | FastAPI + uvicorn SSE |

> Debug CLI 仍可用：`python -m app.cli.debug`。
