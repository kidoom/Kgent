## 2. 核心特性

### 2.1 可插拔 LLM 调用层

- **问题陈述**：现有框架与特定 LLM 服务商强绑定，切换模型需要改代码。
- **方案路径**：LLMProvider 抽象基类 → LLMProviderRegistry 注册中心 → AgentLLM 门面 → 配置驱动选择。
- **设计亮点**：
    - 一个 Provider = 一个类，实现 `chat()` + `chat_stream()` 两个方法
    - 全局注册中心，运行时热替换
    - `.env` 中 `LLM_PROVIDER=openai` 一行切换
- **权衡分析**：

| 维度 | 选项 A：硬编码 | 选项 B：Provider 注册制 | 决策 |
|------|-------------|---------------------|------|
| 扩展性 | 每加一个服务商改核心代码 | 新增 Provider 类 + 一行注册 | B |
| 学习成本 | 简单 | 需理解基类/注册中心 | B（代码量多 50 行但可维护性跃升） |

- **当前状态**：待实现
- **扩展点**：任何兼容 OpenAI 接口的服务只需配置 base_url；私有协议需实现 `LLMProvider`

### 2.2 可插拔工具系统 + MCP 外部网关

- **问题陈述**：工具接入方式不统一，本地工具、远程 API、外部 RAG 项目各自需要不同适配代码。
- **方案路径**：Tool 抽象基类 → ToolRegistry（三种注册方式：Tool 对象 / 裸函数 / MCPTool）→ 统一 `execute_tool(name, arguments) → ToolResult`。
- **设计亮点**：
    - MCP 定位为"统一的外部能力网关"，不是"三种协议之一"
    - 工具来源对 Agent 完全透明
    - 运行时热拔插（`register` / `unregister`）
- **当前状态**：待实现
- **扩展点**：新增工具只需实现 `Tool.run(parameters)` + `Tool.get_parameters()`

### 2.3 Agent 范式

- **问题陈述**：不同任务需要不同的 Agent 推理策略（边想边做 vs 先规划后执行 vs 自我反思）。
- **方案路径**：Agent 抽象基类 → 5 种范式实现，都继承 `Agent.run(input) -> str`。其中 SimpleAgent / ReActAgent 是 v0.1 必做，PlanAndSolveAgent / ReflectionAgent / FunctionCallAgent 可在后续版本逐步加入。
- **权衡分析**：

| 范式 | 工作模式 | 适用场景 |
|------|---------|---------|
| ReAct | Thought→Action→Observation 循环 | 需要外部工具 |
| Plan-Solve | Plan→Execute 两阶段 | 结构化推理 |
| Reflection | Execute→Reflect→Refine 迭代 | 代码生成等高质需求 |
| Simple | 直接对话 + 可选工具 | 简单对话 |
| FunctionCall | 原生 tools / function calling | 支持工具调用协议的模型 |

- **当前状态**：待实现
- **扩展点**：继承 `Agent` 基类，实现自定义 `run()` 方法

### 2.4 链路追踪

- **问题陈述**：Agent 执行链路长（LLM 调用 → 解析 → 工具 → 再调用），出错时靠 print 无法定位。
- **方案路径**：Span 树形数据结构 → Tracer 单例 → Agent 埋点 → TraceExporter 导出（终端树形图 / JSON）。
- **设计亮点**：
    - Context Manager 语法糖：`with tracer.span("llm.call", SpanType.LLM_CALL) as s:`
    - 自动记录耗时、输入/输出截断、异常捕获
    - 不引入外部依赖
- **当前状态**：待实现
- **扩展点**：可接入 Jaeger / OpenTelemetry 导出

### 2.5 记忆系统

- **问题陈述**：LLM 是无状态的，长对话中早期信息会丢失。
- **方案路径**：MemoryTool 内建（Working / Episodic / Semantic 三层），RAG 通过 MCP 外部接入。
- **设计亮点**：对话记忆内建（Agent 强依赖），知识检索外挂（用户自有 RAG 项目 MCP 接入）。
- **当前状态**：待实现

---
