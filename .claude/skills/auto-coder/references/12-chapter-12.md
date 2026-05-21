## 12. 验收标准

V0.1 完成后，必须能通过下面三个场景：

### 12.1 场景 1：纯文本回答

用户输入：

```text
介绍一下你自己
```

期望：

```text
模型直接回答，不调用工具。
```

### 12.2 场景 2：调用计算工具

用户输入：

```text
帮我算一下 12 * 8 + 6
```

期望：

```text
模型输出 calculator tool_use。
runtime 执行 calculator。
tool_result 回填。
模型给出最终答案。
前端展示 think / call / observe / final 步骤（V0.1.2+）。
```

### 12.3 场景 3：读取文件

用户输入：

```text
请读取 README.md 并总结这个项目
```

期望：

```text
模型输出 read_file tool_use。
runtime 读取 README.md。
tool_result 回填。
模型基于文件内容总结。
前端展示 read_file 的调用过程。
```

---

## Part B — Version Log（版本变更日志）
