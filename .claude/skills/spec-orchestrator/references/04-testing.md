## 4. 测试方案

### 4.1 设计理念：TDD

采用测试驱动开发。每个 Agent 范式、每个 Tool、每个 Memory 类型都有对应的单元测试。

### 4.2 测试分层

#### 单元测试覆盖矩阵

| 模块 | 测试重点 | 典型测试用例 |
|------|---------|------------|
| HelloAgentsLLM | Provider 检测、消息格式化 | Mock HTTP 验证各 Provider 路由 |
| Agent 基类 | 消息历史管理、生命周期 | add_message、clear_history 序列化 |
| ReActAgent | Thought/Action 解析、终止条件 | 正则解析、Finish 检测、max_steps 回退 |
| PlanAndSolveAgent | 步骤规划、顺序执行 | `ast.literal_eval` 解析、历史累积 |
| ReflectionAgent | 反思循环、终止条件 | "no improvement" 检测、max_iterations |
| FunctionCallAgent | OpenAI schema 生成、tool_choice | schema 校验、工具执行结果注入 |
| ToolRegistry | 注册、查找、执行 | 两种注册方式、名称冲突报错 |
| MemoryTool | add/search/forget 操作 | TTL 过期、重要度排序、遗忘策略 |
| ContextBuilder | GSSC 流水线 | token 预算填充、分区截断 |
| MCPTool | auto-expansion、工具发现 | Mock MCP Server、工具注册 |

#### 集成测试

| 测试场景 | 验证要点 |
|---------|---------|
| Agent + Tool 完整调用链 | ReAct 循环中工具调用 → 观察 → 终结 |
| Memory + Agent 多轮对话 | 记忆添加 → 检索 → 注入上下文 |
| MCP auto-expansion | 启动 MCP Server → 自动发现工具 → Agent 调用 |
| 评估框架端到端 | 加载数据集 → Agent 预测 → 指标计算 → 报告生成 |

### 4.3 质量指标

| 类别 | 指标 | 目标 |
|------|------|------|
| 单元测试 | 核心逻辑覆盖率 | >= 80% |
| 集成测试 | 关键路径覆盖率 | 100% |
| BFCL | 工具调用准确率 | >= 85% |
| GAIA | L1 准确率 | >= 60% |

### 4.4 黄金测试集

```json
[
  {
    "input": "计算 (3 + 5) * 12 的结果",
    "expected_output": "96",
    "metadata": {"difficulty": "easy", "tags": ["calculator", "simple_agent"]}
  },
  {
    "input": "搜索今天北京的天气，然后告诉我适不适合出门",
    "expected_output": "包含天气信息和建议",
    "metadata": {"difficulty": "medium", "tags": ["react", "multi_tool"]}
  },
  {
    "input": "帮我规划一个三天的杭州旅行",
    "expected_output": "结构化行程",
    "metadata": {"difficulty": "hard", "tags": ["plan_solve", "multi_agent"]}
  }
]
```

---