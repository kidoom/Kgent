## 6. Tool 接口

V0.1 的 Tool 只保留最小字段：

```python
from typing import Protocol

class Tool(Protocol):
    name: str
    description: str
    input_schema: dict

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
