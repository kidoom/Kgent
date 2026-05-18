## 2. 核心特性

### 2.1 多范式 Agent 系统

- **问题陈述**：智能体有多种经典范式（ReAct、Plan-and-Solve、Reflection 等），每种适用于不同场景。学习者需要理解每种范式的原理并能亲手实现。
- **方案路径**：定义统一的 `Agent` 抽象基类，每种范式作为子类实现 `run()` 方法。所有范式共享 LLM、Tool、Message、Config 基础设施。
- **设计亮点**：
    - 统一的 `run(input_text) -> str` 接口，范式对调用方透明
    - 支持 `custom_prompts` 参数，无需修改框架代码即可适配领域场景
    - FunctionCallAgent 支持 OpenAI 原生 function calling，与 prompt-based 方式共存
- **权衡分析**：

| 维度 | Prompt-based Tool Calling | Native Function Calling | 决策 |
|------|--------------------------|------------------------|------|
| 兼容性 | 所有 LLM Provider | 仅 OpenAI 兼容 API | 两种都支持 |
| 可靠性 | 依赖 LLM 输出格式稳定性 | 结构化 JSON，更可靠 | FunctionCall 优先 |
| 可调试性 | 文本输出可直接阅读 | 需解析 JSON | Prompt 更直观 |
| 教学价值 | 展示 LLM 如何"理解"工具 | 展示协议标准 | 两种都有教学意义 |

- **当前状态**：5 种范式已全部实现（Simple、ReAct、Plan-and-Solve、Reflection、FunctionCall）
- **扩展点**：新增范式只需继承 `Agent` 基类，实现 `run()` 方法，在 `agents/__init__.py` 注册即可

### 2.2 可插拔 LLM 多 Provider

- **问题陈述**：不同场景需要不同的 LLM（Azure 企业合规、Ollama 本地隐私、DeepSeek 成本优化），切换 Provider 不应修改业务代码。
- **方案路径**：`HelloAgentsLLM` 封装统一接口，支持 Provider 自动检测（环境变量 → base_url 域名/端口 → API Key 格式）。
- **设计亮点**：
    - 零配置切换：设置 `LLM_BASE_URL` 含 `:11434` 自动选 Ollama，含 `:8000` 自动选 VLLM
    - `_resolve_credentials` 映射 Provider → 环境变量 + 默认 base_url
    - 统一的 `invoke(messages) -> str` 和 `invoke_stream(messages) -> Iterator[str]` 接口
- **权衡分析**：

| 维度 | 自动检测 Provider | 显式配置 Provider | 决策 |
|------|------------------|------------------|------|
| 易用性 | 零配置，开箱即用 | 需要了解配置项 | 自动检测优先 |
| 可预测性 | 偶尔误判 | 100% 确定 | 显式配置作为 fallback |
| 调试难度 | 误判时难排查 | 清晰明确 | 两种都支持 |

- **当前状态**：支持 OpenAI、Azure、Ollama、VLLM、DeepSeek、ModelScope 6 种 Provider
- **扩展点**：新增 Provider 只需在 `_auto_detect_provider` 和 `_resolve_credentials` 中添加分支

### 2.3 统一 Tool 系统

- **问题陈述**：Agent 需要调用外部能力（搜索、计算、MCP 服务、其他 Agent），这些能力的形态各异，需要统一抽象。
- **方案路径**："万物皆工具"——所有能力通过 `Tool` 抽象接口暴露，Agent 通过 `ToolRegistry` 统一调用。
- **设计亮点**：
    - 两种注册方式：`Tool` 子类（完整 schema + 校验）或 `register_function`（快速集成）
    - `ToolChain` 支持多工具顺序编排，模板变量替换
    - `AsyncToolExecutor` 支持 `ThreadPoolExecutor` 并行执行
    - 协议即工具：`MCPTool`、`A2ATool`、`ANPTool` 统一通过 `ToolRegistry` 注册
- **当前状态**：Tool 基类、Registry、Chain、AsyncExecutor、内置工具（Calculator、Search）已实现
- **扩展点**：新增工具只需实现 `Tool` 子类的 `run()` 和 `get_parameters()` 方法

### 2.4 认知记忆系统

- **问题陈述**：Agent 在多轮对话中需要"记住"信息，不同信息有不同的生命周期和检索特征。
- **方案路径**：借鉴认知科学的 Atkinson-Shiffrin 记忆模型，定义 4 层记忆：Working（短期）→ Episodic（事件）→ Semantic（知识图谱）→ Perceptual（多模态）。
- **设计亮点**：
    - `MemoryTool` 统一接口：add/search/forget/consolidate 等 9 种操作
    - 遗忘策略：importance_based、time_based、capacity_based
    - 记忆固化：Working → Episodic → Semantic 按重要度阈值自动晋升
- **权衡分析**：

| 维度 | 仅 WorkingMemory | 4 层记忆系统 | 决策 |
|------|-----------------|-------------|------|
| 复杂度 | 低 | 高 | 渐进式引入 |
| 适用场景 | 单轮/短期对话 | 长期交互、知识积累 | 4 层作为高级特性 |
| 存储依赖 | 无 | SQLite + Qdrant + Neo4j | 可选启用 |

- **当前状态**：4 层记忆全部实现，MemoryTool 统一接口
- **扩展点**：新增记忆类型只需继承 `MemoryModule` 基类，在 `MemoryManager` 中注册

### 2.5 上下文工程（GSSC Pipeline）

- **问题陈述**：LLM 的上下文窗口是有限资源，信息越多边际收益递减（context rot）。需要系统化管理每次推理时 LLM 看到的 token 集合。
- **方案路径**：GSSC 流水线——Gather（收集）→ Select（筛选）→ Structure（结构化）→ Compress（压缩）。
- **设计亮点**：
    - `ContextPacket` 作为信息原子单元（content + timestamp + token_count + relevance_score）
    - 贪心 token 预算填充：`relevance_weight * relevance + recency_weight * recency` 排序后逐个填充
    - 结构化分区：`[Role & Policies]` → `[Task]` → `[Evidence]` → `[Context]` → `[Output]`
    - 长任务策略：Compaction（摘要重启）、NoteTool（结构化笔记）、Sub-agent（子智能体）
- **当前状态**：ContextBuilder、ContextConfig、ContextPacket 已实现
- **扩展点**：自定义 Gather 来源、自定义 Select 策略、自定义 Structure 分区

### 2.6 通信协议集成

- **问题陈述**：Agent 需要与外部工具（MCP）、其他 Agent（A2A）、大规模网络（ANP）通信，每种协议有自己的规范。
- **方案路径**：协议即工具——MCP、A2A、ANP 都封装为 `Tool` 子类，通过 `ToolRegistry` 注册，Agent 无需感知底层协议差异。
- **设计亮点**：
    - `MCPTool` 支持 auto-expansion：自动发现 MCP Server 的所有工具并注册
    - `A2ATool` 支持 Task 生命周期管理（created → negotiated → delegated → in-progress → completed）
    - `ANPTool` 支持服务发现和负载感知路由
- **当前状态**：MCP（基于 FastMCP 2.0）、A2A（基于 a2a-sdk）、ANP（自研）已实现
- **扩展点**：新增协议只需实现 `Tool` 子类，Agent 侧零修改

### 2.7 评估框架

- **问题陈述**：Agent 的能力需要量化评估，不能"凭感觉"调优。
- **方案路径**：三维度评估——BFCL（工具调用准确性）、GAIA（通用问题解决）、LLM Judge（生成质量）。
- **设计亮点**：
    - 评估工具也是 Tool：`BFCLEvaluationTool`、`GAIAEvaluationTool`、`LLMJudgeTool`
    - BFCL 使用 AST 匹配（非字符串比较），容忍参数重排和等价表达
    - GAIA 使用 Quasi Exact Match，类型感知归一化
    - 自动生成 Markdown 报告
- **当前状态**：三个评估域全部实现
- **扩展点**：新增评估域只需实现 `Evaluator` 子类和对应的 `Dataset` 加载器

---