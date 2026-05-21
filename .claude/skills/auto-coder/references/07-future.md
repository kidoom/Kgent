## 7. FastAPI API 设计

### 7.1 `GET /health`

用于存活检查与配置探针：

```json
{
  "status": "ok",
  "provider": "heuristic",
  "available_providers": ["heuristic", "openai"],
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

### 7.2 `POST /api/chat`

请求：

```json
{
  "session_id": "default",
  "message": "请读取 README.md 并总结这个项目"
}
```

响应：

```json
{
  "session_id": "default",
  "answer": "这个项目是...",
  "message_count": 6,
  "steps": [
    {
      "type": "think",
      "turn_index": 0,
      "content": "我先读取 README.md。"
    },
    {
      "type": "call",
      "turn_index": 0,
      "tool_name": "read_file",
      "tool_input": { "path": "README.md" }
    },
    {
      "type": "observe",
      "turn_index": 0,
      "tool_name": "read_file",
      "content": "..."
    },
    {
      "type": "final",
      "turn_index": 1,
      "content": "..."
    }
  ]
}
```

`steps` 是 V0.1.2+ 的可观察 agent loop 轨迹（`think/call/observe/final`），详见 §15。
