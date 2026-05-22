## 1. 目标

实现一个 Python **FastAPI + HTTP/SSE** agent runtime（+ Debug CLI），用来复刻 Claude Code agent loop 的核心骨架。

V0.2.2 起网络入口为 **HTTP 发命令 + SSE 收事件**；曾短暂存在的 standalone WebSocket transport 已于 V0.2.3 移除。

V0.1 不追求强大，只追求把下面这条链路跑通：

```text
user input
  -> messages + tools schema
  -> model
  -> tool_use
  -> runtime executes tool
  -> tool_result back to messages
  -> model
  -> final answer
```

核心学习目标：

```text
模型不是 agent。
agent = model + context + tools + runtime + loop controller。
```
