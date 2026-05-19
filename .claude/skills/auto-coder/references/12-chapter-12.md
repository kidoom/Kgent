## 12. 错误处理

工具执行失败时，不直接让程序崩溃，而是把错误作为 `tool_result` 返回给模型：

```python
ToolResultBlock(
    tool_use_id=tool_use.id,
    content="Error: file not found",
    is_error=True,
)
```

这样模型可以根据错误继续修正下一步动作。
