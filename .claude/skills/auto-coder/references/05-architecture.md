## 5. Message 协议

V0.1 使用四类消息：

```python
from typing import Literal
from pydantic import BaseModel

class ToolUseBlock(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict

class ToolResultBlock(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[ToolUseBlock] | list[ToolResultBlock]
```

`tool_use` 由 assistant 产生：

```json
{
  "type": "tool_use",
  "id": "toolu_123",
  "name": "read_file",
  "input": {
    "path": "README.md"
  }
}
```

`tool_result` 作为 user message 回填。

关键原则：

```text
assistant = 模型意图
tool_result = 外部观察
```
