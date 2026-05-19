## 1. 目标

实现一个 Python + FastAPI 版本的最小可运行 agent runtime，用来复刻 Claude Code agent loop 的核心骨架。

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
