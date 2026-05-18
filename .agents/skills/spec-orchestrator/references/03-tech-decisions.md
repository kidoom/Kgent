## 3. 技术选型

### 3.1 LLM 调用层

**目标：** 定义统一的 LLM 调用接口，支持多 Provider 无缝切换。

#### 3.1.1 HelloAgentsLLM

**接口定义：**

```python
class HelloAgentsLLM:
    def __init__(self, model=None, api_key=None, base_url=None,
                 provider=None, timeout=30, **kwargs):
        """支持显式指定 provider 或自动检测"""
        ...

    def invoke(self, messages: list[dict], temperature: float = 0) -> str:
        """同步调用，返回完整响应文本"""
        ...

    def invoke_stream(self, messages: list[dict], temperature: float = 0) -> Iterator[str]:
        """流式调用，逐 token 返回"""
        ...
```

**Provider 自动检测逻辑：**
1. 检查环境变量：`MODELSCOPE_API_KEY` → ModelScope，`OPENAI_API_KEY` → OpenAI
2. 解析 base_url：`:11434` → Ollama，`:8000` → VLLM，`azure` 域名 → Azure
3. 检查 API Key 格式：特定前缀 → 对应 Provider

**配置：**
```yaml
llm:
  provider: auto  # auto | openai | azure | ollama | deepseek | modelscope
  model: gpt-4o
  api_key: "${LLM_API_KEY}"
  base_url: "${LLM_BASE_URL}"
  timeout: 30
```

**降级策略：** Provider 检测失败时默认走 OpenAI 兼容模式，使用 base_url + api_key 直连。

### 3.2 Agent 范式层

**目标：** 定义统一的 Agent 抽象，支持多种推理范式。

#### 3.2.1 Agent 基类

```python
class Agent(ABC):
    def __init__(self, name: str, llm: HelloAgentsLLM,
                 system_prompt: str = "", config: Config = None):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """核心执行方法，子类必须实现"""
        ...

    def add_message(self, role: str, content: str, **metadata):
        """添加消息到历史"""
        ...

    def clear_history(self):
        """清空对话历史"""
        ...

    def get_history(self) -> list[dict]:
        """获取历史（OpenAI 格式）"""
        ...
```

#### 3.2.2 五种范式实现

| 范式 | 核心循环 | 工具调用方式 | 适用场景 |
|------|---------|------------|---------|
| **SimpleAgent** | 单次 LLM 调用 + 可选工具循环 | `[TOOL_CALL:name:params]` 文本解析 | 简单问答、工具调用 |
| **ReActAgent** | Thought → Action → Observation 循环 | `Action: ToolName[input]` 文本解析 | 需要推理的复杂任务 |
| **PlanAndSolveAgent** | 先规划步骤列表，再逐步执行 | 无工具调用，纯 LLM 推理 | 需要结构化分解的任务 |
| **ReflectionAgent** | 执行 → 反思 → 改进 循环 | 无工具调用，纯 LLM 迭代 | 需要自我纠错的任务 |
| **FunctionCallAgent** | OpenAI 原生 function calling | `tools` schema + `tool_choice` | 生产级工具调用 |

**配置：**
```yaml
agent:
  default_type: simple  # simple | react | plan_solve | reflection | function_call
  max_steps: 5          # ReAct 最大步数
  max_iterations: 3     # Reflection 最大迭代次数
  max_tool_iterations: 10  # SimpleAgent 工具调用最大轮数
```

### 3.3 Tool 系统

**目标：** 定义统一的工具接口，支持函数注册、Tool 子类、ToolChain、异步执行。

#### 3.3.1 Tool 抽象接口

```python
class Tool(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def run(self, parameters: dict) -> str:
        """执行工具"""
        ...

    @abstractmethod
    def get_parameters(self) -> list[ToolParameter]:
        """返回参数定义"""
        ...

    def to_openai_schema(self) -> dict:
        """生成 OpenAI function calling JSON schema"""
        ...
```

#### 3.3.2 ToolRegistry

```python
class ToolRegistry:
    def register_tool(self, tool: Tool):
        """注册 Tool 子类实例"""
        ...

    def register_function(self, name: str, description: str, func: callable):
        """快速注册普通函数为工具"""
        ...

    def get_tools_description(self) -> str:
        """获取所有工具的文本描述（用于 prompt）"""
        ...

    def execute_tool(self, name: str, input_data: any) -> str:
        """按名称执行工具"""
        ...
```

**配置：**
```yaml
tools:
  builtin:
    calculator: true
    search: true
  custom: []  # 用户自定义工具列表
```

### 3.4 记忆系统

**目标：** 定义 4 层认知记忆，支持渐进式启用。

#### 3.4.1 MemoryTool 统一接口

| 操作 | 说明 | 参数 |
|------|------|------|
| `add` | 添加记忆 | `content`, `memory_type`, `importance` |
| `search` | 检索记忆 | `query`, `memory_type`, `top_k` |
| `forget` | 遗忘记忆 | `strategy` (importance/time/capacity) |
| `consolidate` | 固化记忆 | 按阈值从 Working 晋升到 Episodic/Semantic |
| `summary` | 记忆摘要 | `memory_type` |
| `stats` | 统计信息 | 无 |

**4 层记忆配置：**
```yaml
memory:
  working:
    enabled: true
    max_items: 50
    ttl_minutes: 60
  episodic:
    enabled: false  # 需要 SQLite
    db_path: ./data/episodic.db
  semantic:
    enabled: false  # 需要 Neo4j + Qdrant
    neo4j_uri: "${NEO4J_URI}"
    qdrant_url: "${QDRANT_URL}"
  perceptual:
    enabled: false  # 需要 CLIP/CLAP 模型
```

### 3.5 上下文工程

**目标：** 定义 GSSC 流水线，系统化管理 LLM 上下文窗口。

#### 3.5.1 ContextBuilder

```python
class ContextBuilder:
    def __init__(self, config: ContextConfig,
                 memory_tool: MemoryTool = None,
                 rag_tool: RAGTool = None):
        ...

    def build(self, query: str, system_prompt: str = "",
              history: list[Message] = None,
              custom_packets: list[ContextPacket] = None) -> list[dict]:
        """执行 GSSC 流水线，返回 messages 列表"""
        # 1. Gather: 从各来源收集 ContextPacket
        # 2. Select: 按 relevance + recency 排序，贪心填充 token 预算
        # 3. Structure: 按分区组织
        # 4. Compress: 超出预算时逐分区截断
        ...
```

**配置：**
```yaml
context:
  max_tokens: 8000
  reserve_ratio: 0.15  # 系统指令预留比例
  min_relevance: 0.3
  recency_weight: 0.3
  relevance_weight: 0.7
  enable_compression: true
```

### 3.6 通信协议

**目标：** 将 MCP、A2A、ANP 封装为 Tool，Agent 侧零修改。

#### 3.6.1 协议即工具

| 协议 | Tool 类 | 核心能力 | 依赖 |
|------|---------|---------|------|
| **MCP** | `MCPTool` | auto-expansion：自动发现 Server 所有工具 | FastMCP 2.0 |
| **A2A** | `A2ATool` | Task 生命周期管理，Agent-to-Agent 通信 | a2a-sdk |
| **ANP** | `ANPTool` | 服务发现 + 负载感知路由 | 自研 |

**配置：**
```yaml
protocols:
  mcp:
    servers:
      - name: amap
        command: ["npx", "amap-mcp-server"]
        auto_expand: true
  a2a:
    agents: []
  anp:
    discovery_url: ""
```

### 3.7 评估框架

**目标：** 定义 3 维评估体系，评估工具封装为 Tool。

| 评估域 | 指标 | 评估方法 |
|-------|------|---------|
| **BFCL**（工具调用） | Accuracy, Weighted Accuracy, Error Rate | AST 匹配 |
| **GAIA**（通用能力） | Exact Match Rate, Level-wise Accuracy | Quasi Exact Match |
| **数据质量** | Average Score, Pass Rate, Win Rate | LLM Judge + 人工验证 |

**配置：**
```yaml
evaluation:
  bfcl:
    enabled: true
    dataset_path: ./data/bfcl/
  gaia:
    enabled: true
    dataset_path: ./data/gaia/
  llm_judge:
    enabled: true
    judge_model: gpt-4o
```

---