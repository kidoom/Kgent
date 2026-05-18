## 5. 系统架构与模块设计

### 5.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     应用层（Applications）                        │
│   旅行助手 | 深度研究 | 赛博小镇 | 用户自定义应用                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     Agent 范式层（Agents）                        │
│   SimpleAgent | ReActAgent | PlanAndSolveAgent                  │
│   ReflectionAgent | FunctionCallAgent                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     能力层（Capabilities）                        │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Tool 系统 │  │ Memory   │  │ Context  │  │ Protocol │       │
│  │ Registry │  │ 4层记忆  │  │ GSSC     │  │ MCP/A2A  │       │
│  │ Chain    │  │ 遗忘固化 │  │ Pipeline │  │ ANP      │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     核心层（Core）                                │
│   Agent(ABC) | HelloAgentsLLM | Message | Config | Exceptions  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     基础设施层（Infrastructure）                  │
│   结构化日志 | Trace Context | 评估框架 | 配置管理               │
└─────────────────────────────────────────────────────────────────┘
```

**层级依赖规则：**
- 应用层 → Agent 范式层 → 能力层 → 核心层 → 基础设施层
- 禁止循环依赖。能力层之间可组合（如 ContextBuilder 使用 MemoryTool）但不互相依赖。

### 5.2 目录结构

```
hello_agents/
│
├── core/                                # 核心层
│   ├── __init__.py
│   ├── agent.py                         # Agent 抽象基类
│   ├── llm.py                           # HelloAgentsLLM（多 Provider）
│   ├── message.py                       # Message 数据模型
│   ├── config.py                        # Config 配置模型
│   └── exceptions.py                    # 自定义异常
│
├── agents/                              # Agent 范式层
│   ├── __init__.py
│   ├── simple_agent.py                  # SimpleAgent
│   ├── react_agent.py                   # ReActAgent
│   ├── plan_solve_agent.py              # PlanAndSolveAgent
│   ├── reflection_agent.py              # ReflectionAgent
│   └── function_call_agent.py           # FunctionCallAgent
│
├── tools/                               # Tool 系统
│   ├── __init__.py
│   ├── base.py                          # Tool 抽象基类 + ToolParameter
│   ├── registry.py                      # ToolRegistry
│   ├── chain.py                         # ToolChain + ToolChainManager
│   ├── async_executor.py                # AsyncToolExecutor
│   └── builtin/                         # 内置工具
│       ├── calculator.py
│       └── search.py
│
├── memory/                              # 记忆系统
│   ├── __init__.py
│   ├── memory_tool.py                   # MemoryTool 统一接口
│   ├── memory_manager.py                # MemoryManager 协调器
│   ├── working_memory.py                # WorkingMemory（内存 + TTL）
│   ├── episodic_memory.py               # EpisodicMemory（SQLite + Qdrant）
│   ├── semantic_memory.py               # SemanticMemory（Neo4j + Qdrant）
│   └── perceptual_memory.py             # PerceptualMemory（多模态）
│
├── context/                             # 上下文工程
│   ├── __init__.py
│   ├── context_builder.py               # ContextBuilder（GSSC Pipeline）
│   ├── context_config.py                # ContextConfig
│   └── context_packet.py                # ContextPacket
│
├── protocols/                           # 通信协议
│   ├── __init__.py
│   ├── mcp/
│   │   ├── mcp_tool.py                  # MCPTool
│   │   └── mcp_server.py                # MCPServer 封装
│   ├── a2a/
│   │   ├── a2a_tool.py                  # A2ATool
│   │   └── a2a_server.py                # A2AServer 封装
│   └── anp/
│       ├── anp_tool.py                  # ANPTool
│       └── anp_discovery.py             # 服务发现
│
├── evaluation/                          # 评估框架
│   ├── __init__.py
│   ├── benchmarks/
│   │   ├── bfcl/                        # 工具调用评估
│   │   ├── gaia/                        # 通用能力评估
│   │   └── data_generation/             # 数据质量评估
│   └── tools/                           # 评估 Tool 封装
│       ├── bfcl_evaluation_tool.py
│       ├── gaia_evaluation_tool.py
│       ├── llm_judge_tool.py
│       └── win_rate_tool.py
│
├── observability/                       # 基础设施层
│   ├── __init__.py
│   ├── logger.py                        # 结构化日志
│   └── trace_context.py                 # Trace 上下文
│
├── config/                              # 配置文件
│   └── settings.yaml                    # 主配置
│
├── tests/                               # 测试
│   ├── unit/                            # 单元测试
│   ├── integration/                     # 集成测试
│   └── fixtures/                        # 测试数据
│
├── examples/                            # 示例代码
│   ├── travel_assistant/                # 旅行助手
│   ├── deep_research/                   # 深度研究
│   └── cyber_town/                      # 赛博小镇
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

### 5.3 模块说明

#### 5.3.1 核心层

| 模块 | 职责 | 关键技术点 |
|------|------|----------|
| `agent.py` | Agent 抽象基类 | ABC、消息历史管理、run() 抽象方法 |
| `llm.py` | 统一 LLM 调用 | Provider 自动检测、流式输出、凭据解析 |
| `message.py` | 消息数据模型 | Pydantic BaseModel、OpenAI 格式序列化 |
| `config.py` | 配置管理 | Pydantic BaseModel、from_env() 环境变量加载 |
| `exceptions.py` | 自定义异常 | AgentError、ToolError、ConfigError |

#### 5.3.2 Agent 范式层

| 模块 | 职责 | 关键技术点 |
|------|------|----------|
| `simple_agent.py` | 单次调用 + 工具循环 | `[TOOL_CALL:]` 正则解析、max_tool_iterations |
| `react_agent.py` | 推理-行动循环 | Thought/Action/Observation 模式、Finish 终止 |
| `plan_solve_agent.py` | 规划-执行 | `ast.literal_eval` 步骤解析、历史累积 |
| `reflection_agent.py` | 反思迭代 | Memory 类型记录、"no improvement" 终止 |
| `function_call_agent.py` | 原生工具调用 | OpenAI tools schema、tool_choice |

#### 5.3.3 能力层

| 模块 | 职责 | 关键技术点 |
|------|------|----------|
| `tools/base.py` | Tool 抽象 | ABC、ToolParameter Pydantic 模型、to_openai_schema() |
| `tools/registry.py` | 工具注册中心 | 双注册路径（Tool 子类 / 函数） |
| `tools/chain.py` | 工具链编排 | 顺序执行、模板变量替换 |
| `memory/memory_tool.py` | 记忆统一接口 | 9 种操作、Tool 子类封装 |
| `context/context_builder.py` | 上下文构建 | GSSC Pipeline、token 预算贪心填充 |
| `protocols/mcp/mcp_tool.py` | MCP 集成 | FastMCP 2.0、auto-expansion |

#### 5.3.4 基础设施层

| 模块 | 职责 | 关键技术点 |
|------|------|----------|
| `logger.py` | 结构化日志 | JSON Formatter、DEBUG/INFO/WARNING 级别 |
| `trace_context.py` | 请求追踪 | trace_id 生成、阶段耗时记录 |

### 5.4 数据流图

#### 5.4.1 Agent 执行流（以 ReAct 为例）

```
用户输入: "今天北京天气怎么样？"
      │
      ▼
┌─────────────────┐
│  ReActAgent.run()│
│  构建 messages   │  [system_prompt] + [history] + [user_input]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  HelloAgentsLLM  │  调用 LLM API
│  .invoke()       │
└────────┬────────┘
         │ LLM 输出: "Thought: 我需要搜索天气\nAction: search[北京今天天气]"
         ▼
┌─────────────────┐
│  _parse_output() │  正则解析 Thought 和 Action
└────────┬────────┘
         │ Action = "search[北京今天天气]"
         ▼
┌─────────────────┐
│ ToolRegistry     │  执行 search 工具
│ .execute_tool()  │
└────────┬────────┘
         │ Observation: "北京今天晴，25°C"
         ▼
┌─────────────────┐
│ 追加到 history   │  "Action: search[...]\nObservation: ..."
│ 下一轮循环       │
└────────┬────────┘
         │ LLM 输出: "Thought: 我已有答案\nAction: Finish[北京今天晴，25°C...]"
         ▼
      返回最终答案
```

#### 5.4.2 记忆固化流

```
用户对话
      │
      ▼
┌─────────────────┐
│ WorkingMemory   │  内存存储，TTL=60min，上限50条
│ (add)           │
└────────┬────────┘
         │ 定时检查 importance >= threshold
         ▼
┌─────────────────┐
│ EpisodicMemory  │  SQLite 持久化，事件索引
│ (consolidate)   │
└────────┬────────┘
         │ 重要度持续高于阈值
         ▼
┌─────────────────┐
│ SemanticMemory  │  Neo4j 知识图谱 + Qdrant 向量
│ (consolidate)   │
└─────────────────┘
```

### 5.5 配置驱动设计

```yaml
# config/settings.yaml

llm:
  provider: auto
  model: gpt-4o
  api_key: "${LLM_API_KEY}"
  base_url: "${LLM_BASE_URL}"
  timeout: 30

agent:
  default_type: simple
  max_steps: 5
  max_iterations: 3
  max_tool_iterations: 10

tools:
  builtin:
    calculator: true
    search: true

memory:
  working:
    enabled: true
    max_items: 50
    ttl_minutes: 60
  episodic:
    enabled: false
  semantic:
    enabled: false

context:
  max_tokens: 8000
  reserve_ratio: 0.15
  recency_weight: 0.3
  relevance_weight: 0.7
  enable_compression: true

protocols:
  mcp:
    servers: []

evaluation:
  bfcl:
    enabled: false
  gaia:
    enabled: false

observability:
  enabled: true
  log_level: INFO
```

### 5.6 扩展性设计要点

1. **新增 Agent 范式**：继承 `Agent` 基类，实现 `run()` 方法，在 `agents/__init__.py` 注册
2. **新增 LLM Provider**：在 `llm.py` 的 `_auto_detect_provider` 和 `_resolve_credentials` 中添加分支
3. **新增 Tool**：实现 `Tool` 子类的 `run()` 和 `get_parameters()`，或用 `register_function` 快速注册
4. **新增 Memory 类型**：继承 `MemoryModule` 基类，在 `MemoryManager` 中注册
5. **新增通信协议**：实现 `Tool` 子类封装协议调用，Agent 侧零修改
6. **新增评估域**：实现 `Evaluator` 子类和 `Dataset` 加载器

---