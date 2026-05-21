## 10. 运行时合约

### 10.1 串行执行

V0.1 先全部串行执行：

```text
模型一次输出多个 tool_use
  -> 按输出顺序逐个执行
  -> 每个结果都追加为 tool_result
  -> 再进入下一轮模型请求
```

不做 safe / unsafe 并发分类。

### 10.2 错误处理

工具执行失败时，不直接让程序崩溃，而是把错误作为 `tool_result` 返回给模型：

```python
ToolResultBlock(
    tool_use_id=tool_use.id,
    content="Error: file not found",
    is_error=True,
)
```

这样模型可以根据错误继续修正下一步动作。

### 10.3 安全边界

V0.1 的安全策略：

- `read_file` 只能读取项目目录内文件
- 禁止读取绝对路径
- 禁止读取包含 `..` 的路径
- 禁止执行 shell 命令
- 禁止写文件
- `max_steps` 默认设置为 8，防止无限循环
