## 6. Tool 协议

V0.1 的 Tool 只保留最小字段：

```python
from typing import Protocol

class Tool(Protocol):
    name: str
    description: str
    input_schema: dict
    risk_level: Literal["low", "medium", "high"]  # runtime-only，见 §18

    async def call(self, input: dict) -> str:
        ...
```

模型看到的是 schema 投影：

```python
def tool_to_schema(tool: Tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }
```

内部设计原则：

```text
runtime 保存完整 Tool 对象。
model request 只接收 ToolSchema。
```

> V0.2 起 `risk_level` 为 runtime 元数据，**不**通过 `tool_to_schema()` 投影给模型。详见 §18。

