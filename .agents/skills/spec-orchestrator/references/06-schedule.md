## 6. 项目排期

### 6.1 排期原则

- 只按本 SPEC 设计落地，每步产出可见的文件系统变化。
- 一小时一可验收增量，TDD 优先。
- 先打通主闭环（Core → SimpleAgent → Tool → LLM），再补齐高级特性。
- 外部依赖（LLM API、Qdrant、Neo4j）在单元测试中 Mock。

### 6.2 阶段总览

| 阶段 | 目的 | 核心交付物 |
|------|------|-----------|
| **A** | 工程骨架与测试基座 | 目录结构、pytest 配置、Config 加载 |
| **B** | 核心层 | Agent ABC、HelloAgentsLLM、Message、Exceptions |
| **C** | Tool 系统 | Tool ABC、ToolRegistry、ToolChain、内置工具 |
| **D** | Agent 范式 | Simple → ReAct → PlanAndSolve → Reflection → FunctionCall |
| **E** | 记忆系统 | MemoryTool、MemoryManager、WorkingMemory、EpisodicMemory |
| **F** | 上下文工程 | ContextBuilder、ContextPacket、GSSC Pipeline |
| **G** | 通信协议 | MCPTool、A2ATool、ANPTool |
| **H** | 评估框架 | BFCL/GAIA/LLM Judge 评估工具 |
| **I** | 综合应用 | 旅行助手、深度研究案例 |
| **J** | 验收与文档 | E2E 测试、README、发布准备 |

### 6.3 进度跟踪表

> **状态**：`[ ]` 未开始 | `[~]` 进行中 | `[x]` 已完成

#### 阶段 A：工程骨架

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| A1 | 初始化目录树与 pyproject.toml | [ ] | | |
| A2 | pytest 配置与测试目录 | [ ] | | |
| A3 | Config 加载（settings.yaml + from_env） | [ ] | | |
| A4 | 自定义异常类（exceptions.py） | [ ] | | |

#### 阶段 B：核心层

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| B1 | Message 数据模型（Pydantic） | [ ] | | |
| B2 | HelloAgentsLLM 基础（单 Provider: OpenAI） | [ ] | | |
| B3 | HelloAgentsLLM 多 Provider + 自动检测 | [ ] | | |
| B4 | Agent 抽象基类 | [ ] | | |

#### 阶段 C：Tool 系统

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| C1 | Tool ABC + ToolParameter | [ ] | | |
| C2 | ToolRegistry（双注册路径） | [ ] | | |
| C3 | to_openai_schema() 生成 | [ ] | | |
| C4 | ToolChain + ToolChainManager | [ ] | | |
| C5 | AsyncToolExecutor | [ ] | | |
| C6 | 内置工具：Calculator + Search | [ ] | | |

#### 阶段 D：Agent 范式

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| D1 | SimpleAgent（单次调用） | [ ] | | |
| D2 | SimpleAgent + Tool 调用循环 | [ ] | | |
| D3 | ReActAgent（Thought/Action/Observation） | [ ] | | |
| D4 | PlanAndSolveAgent（规划-执行） | [ ] | | |
| D5 | ReflectionAgent（反思迭代） | [ ] | | |
| D6 | FunctionCallAgent（OpenAI 原生） | [ ] | | |

#### 阶段 E：记忆系统

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| E1 | MemoryTool 统一接口（9 种操作） | [ ] | | |
| E2 | MemoryManager 协调器 | [ ] | | |
| E3 | WorkingMemory（内存 + TTL + TF-IDF） | [ ] | | |
| E4 | EpisodicMemory（SQLite + 向量检索） | [ ] | | |
| E5 | 遗忘策略 + 固化机制 | [ ] | | |

#### 阶段 F：上下文工程

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| F1 | ContextPacket + ContextConfig | [ ] | | |
| F2 | ContextBuilder Gather 阶段 | [ ] | | |
| F3 | ContextBuilder Select + Structure + Compress | [ ] | | |
| F4 | 长任务策略：Compaction + NoteTool | [ ] | | |

#### 阶段 G：通信协议

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| G1 | MCPTool + auto-expansion | [ ] | | |
| G2 | MCPServer 封装 | [ ] | | |
| G3 | A2ATool + Task 生命周期 | [ ] | | |
| G4 | ANPTool + 服务发现 | [ ] | | |

#### 阶段 H：评估框架

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| H1 | BFCL 评估工具（AST 匹配） | [ ] | | |
| H2 | GAIA 评估工具（Quasi Exact Match） | [ ] | | |
| H3 | LLM Judge + Win Rate 工具 | [ ] | | |
| H4 | 评估报告自动生成 | [ ] | | |

#### 阶段 I：综合应用

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| I1 | 旅行助手案例（多 Agent + MCP） | [ ] | | |
| I2 | 深度研究案例（TODO 驱动） | [ ] | | |
| I3 | 案例文档与 README | [ ] | | |

#### 阶段 J：验收与文档

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| J1 | E2E：Agent 全范式验收测试 | [ ] | | |
| J2 | E2E：Tool 系统验收测试 | [ ] | | |
| J3 | 完善 README + API 文档 | [ ] | | |
| J4 | PyPI 发布准备 | [ ] | | |

#### 总体进度

| 阶段 | 总任务 | 已完成 | 进度 |
|------|-------|--------|------|
| A | 4 | 0 | 0% |
| B | 4 | 0 | 0% |
| C | 6 | 0 | 0% |
| D | 6 | 0 | 0% |
| E | 5 | 0 | 0% |
| F | 4 | 0 | 0% |
| G | 4 | 0 | 0% |
| H | 4 | 0 | 0% |
| I | 3 | 0 | 0% |
| J | 4 | 0 | 0% |
| **总计** | **44** | **0** | **0%** |