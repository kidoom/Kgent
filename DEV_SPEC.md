# DEV_SPEC: Kagent
> Version: 0.1 Draft — 2026-05-06
> 项目类型：Library/SDK（AI Agent 框架）
> 参考文档：Hello-Agents框架实现全景文档.md

> 命名约定：项目名使用 `Kagent`，Python 包名与 import 路径使用 `kagent`。

---

## 1. 项目概述

### 1.1 背景

`Kagent` 是一个 pip 可安装的 AI-Native Agent 框架，让开发者用最少代码构建能自主推理、调用工具、与外部服务协作的 LLM 智能体。

本项目通过 **可插拔注册制 + 配置驱动** 架构解决 **Agent 框架学习曲线陡峭、与特定服务商强绑定、新增能力需要大量编码** 的问题。

### 1.2 设计理念

> **核心定位：最小内核 + 万物皆可插拔**

现有 Agent 框架要么过度抽象（LangChain）、要么与特定模型绑定、要么黑盒化。Kagent 的设计哲学：框架本身只提供最小组装层，LLM Provider、Tool、MCP、RAG 全部以插件形态接入。切换 LLM 服务商 = 改一行 .env 配置。

#### 1）可插拔注册制（"新增 = 写一个类 + 一行注册"）

LLM Provider、Tool、MCP 外部服务均通过 Registry 接入。框架内核不依赖任何具体实现。每种组件有统一抽象基类 + 工厂模式 + 配置驱动选择。

#### 2）配置驱动（"切换只改配置表，代码零改动"）

所有行为由 `settings.yaml` / `.env` 控制：LLM Provider 选择、Provider 凭证、模型 ID、工具开关、日志级别等。

#### 3）链路追踪是基础设施（"Agent 出问题不靠 print 大海捞针"）

每次 Agent 运行的完整执行树、每步耗时、LLM 输入/输出、工具参数/结果全部结构化记录，支持终端树形图和 JSON 双格式导出。

### 1.3 目标受众

| 受众 | 获得什么 | 使用方式 |
|------|---------|---------|
| AI 应用开发者 | 快速构建 Agent 应用 | `pip install kagent` → `from kagent import ...` |
| Agent 学习者 | 框架源码可读，渐进式学习 | 按阶段构建，每阶段可独立运行 |
| 工具开发者 | 写一个 Tool/Provider 即可接入 | 实现 `Tool.run()` 或 `LLMProvider.chat()` |

### 1.4 范围边界

**v0.1 MVP 必须完成：**
- pip 可安装的 `kagent` 包与最小目录骨架
- LLM Provider 抽象、注册中心、OpenAI 兼容 Provider、配置驱动选择
- Tool 抽象、ToolRegistry、CalculatorTool、SearchTool（真实外部搜索测试可跳过）
- SimpleAgent / ReActAgent 两种基础 Agent
- Tracer / Span / TraceExporter 基础链路追踪
- 单元测试、Mock 集成测试、最小 README 示例

**MVP 硬截止线：A1-A8 + B1-B3 + C1-C3 + C8（Config + 异常体系 + pip install 验证）。** C4-C7/C9（多 Provider 扩展、Agent 加固）以及 D/E/F 阶段全部属于 v0.2+。

### 1.4.1 子项目分解

本 spec 覆盖范围较大，按 Superpowers 方法论应分解为独立子项目，每个有自己的 spec → plan → implement 循环：

| 子项目 | 包含阶段 | 可独立交付 | 依赖 |
|--------|---------|-----------|------|
| **Kagent Core** | A + B + C | ✅ pip install 后就能用 SimpleAgent/ReActAgent | 无 |
| **Kagent Observability** | D | ✅ Tracer + MCP + 容错，可接入 Core | Core |
| **Kagent Memory** | E | ✅ 记忆系统 + ContextBuilder，可接入 Core | Core |
| **Examples** | F | ✅ 三个实战项目骨架 | Core + Memory |

每个子项目应在完成前一个之后再启动（Core → Observability → Memory → Examples）。Memory 和 Observability 可并行。

**v0.1 范围内（＝ MVP 硬截止线以上）：**
- LLM 调用层（可插拔 Provider 注册制，内置 OpenAI，其余 Provider 为 v0.2+）
- 2 种 Agent 范式（SimpleAgent / ReActAgent）
- 可插拔工具系统（本地 Tool + 裸函数注册）
- 基础链路追踪（Tracer + Span + TraceExporter）
- Config 类 + 异常体系 + pip install

**v0.2+（后续版本，不在本 spec 的实施范围内）：**
- 5 种 Agent 范式补齐（PlanAndSolveAgent / ReflectionAgent / FunctionCallAgent）
- 多 Provider 扩展（ModelScope/Zhipu/Ollama/VLLM + auto-detect）
- MCP 远程服务 + 容错重试 + 监控
- MemoryTool（Working / Episodic / Semantic 三层记忆）
- ContextBuilder（GSSC 上下文流水线）
- 3 个实战参考项目（旅行助手 / 深度研究 / 赛博小镇）

**v0.1 后续路线：**
- v0.2（子项目：Kagent Core 增强）：多 Provider（ModelScope/Zhipu/Ollama/VLLM + auto-detect）、FunctionCallAgent + PlanAndSolveAgent + ReflectionAgent
- v0.3（子项目：Kagent Observability）：MCPTool、并行工具调用、容错重试、监控告警
- v0.4（子项目：Kagent Memory）：MemoryManager、Working/Episodic/Semantic Memory、ContextBuilder
- examples（子项目：Examples）：旅行助手 / 深度研究 / 赛博小镇作为框架能力验收样例，不阻塞核心包发布

**明确排除：**
- RAG 引擎实现 — 用户自有 RAG 项目通过 MCP 接入
- 前端 UI — 实战项目的前端独立于框架
- 模型训练管道 — Agentic RL 章节独立于框架核心
- 评估基准运行器 — BFCL/GAIA 作为独立脚本

---

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

## 3. 技术选型

### 3.0 依赖清单（Dependency Manifest）

> `pyproject.toml` 的 `[project.dependencies]` 和 `[project.optional-dependencies]` 必须按此表声明，不得遗漏或自行引入未列出的库。同时维护 `requirements.txt`（核心依赖）和 `requirements-dev.txt`（含 `-r requirements.txt` + 开发依赖），让开源用户 `pip install -r requirements.txt` 即可快速搭建环境。

#### 核心依赖（`pip install kagent`）

| 包名 | 版本约束 | 用途 | 引入阶段 |
|------|---------|------|---------|
| `openai` | `>=1.0` | OpenAI 兼容 LLM 调用（`chat.completions.create`） | A |
| `pydantic` | `>=2.0` | 数据模型校验（`BaseModel`, `Field`, `ValidationError`） | A |
| `python-dotenv` | `>=1.0` | `.env` 文件加载到 `os.environ` | A |
| `httpx` | `>=0.24` | HTTP 客户端（`openai` 内部依赖 + LLM 超时/限流处理） | A |

#### 可选依赖（`pip install kagent[mcp]` / `kagent[examples]`）

| 包名 | 版本约束 | 用途 | 引入阶段 | extra name |
|------|---------|------|---------|-----------|
| `mcp` | `>=1.0` | MCP 协议客户端（`MCPTool` 连接外部 MCP Server） | D | `mcp` |
| `numpy` | `>=1.24` | SemanticMemory 向量检索（余弦相似度计算） | E | `memory` |
| `fastapi` | `>=0.100` | 实战示例的 HTTP API 入口 | F | `examples` |
| `uvicorn` | `>=0.20` | ASGI 服务器（配合 FastAPI） | F | `examples` |

#### 开发依赖（`pip install kagent[dev]`）

| 包名 | 版本约束 | 用途 |
|------|---------|------|
| `pytest` | `>=7.0` | 单元/集成测试框架 |
| `pytest-cov` | `>=4.0` | 覆盖率报告 |
| `pytest-asyncio` | `>=0.21` | async 测试支持（为后续 async Agent 预留） |

#### 标准库（无需声明，仅作记录）

| 模块 | 用途 | 引入阶段 |
|------|------|---------|
| `ast` | CalculatorTool 安全表达式解析（`ast.literal_eval`） | A |
| `re` | Agent 输出正则解析（Thought/Action 提取） | B |
| `uuid` | `run_id` 生成、`trace_id` / `span_id` 生成 | B/D |
| `dataclasses` | `Span` 数据类定义（`@dataclass` + `field`） | D |
| `contextvars` | `Tracer` 并发隔离（`ContextVar`） | D |
| `time` | `start_time` / `end_time` 记录 | D |
| `json` | Trace JSON 导出 + MCP 消息序列化 | D |
| `subprocess` | MCP Server 子进程启动/管理 | D |
| `sqlite3` | EpisodicMemory 持久化 | E |
| `collections` | `OrderedDict`（WorkingMemory 容量淘汰） | E |
| `typing` | 类型注解（`Literal`, `Iterator`, `Any`） | 全阶段 |

#### requirements.txt

```
# pip install -r requirements.txt
pydantic>=2.0
openai>=1.0
python-dotenv>=1.0
httpx>=0.24
```

> `requirements.txt` 与 `pyproject.toml` 的 `[project.dependencies]` 必须保持同步。`requirements-dev.txt` 以 `-r requirements.txt` 开头，追加 dev 依赖。

#### pyproject.toml 完整声明

```toml
[project]
name = "kagent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "openai>=1.0",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "httpx>=0.24",
]

[project.optional-dependencies]
mcp = ["mcp>=1.0"]
memory = ["numpy>=1.24"]
examples = ["fastapi>=0.100", "uvicorn>=0.20"]
dev = ["pytest>=7.0", "pytest-cov>=4.0", "pytest-asyncio>=0.21"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "external: 真实 API 测试，CI 默认跳过（需 API Key）",
]
```

### 3.1 LLM 调用层

#### 3.1.1 LLMProvider

**接口定义：**
```python
class LLMResponse(BaseModel):
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    usage: dict | None = None       # {"prompt": int, "completion": int, "total": int}
    raw: Any = None                 # Provider 原始响应，默认不进入日志

class LLMChunk(BaseModel):
    delta: str
    usage: dict | None = None
    raw: Any = None

class LLMProvider(ABC):
    """LLM 服务商抽象基类 — 所有 Provider 必须实现"""
    @abstractmethod
    def chat(self, messages: list[dict], model: str,
             temperature: float, tools: list[dict] | None = None,
             tool_choice: str | dict | None = None) -> LLMResponse: ...

    @abstractmethod
    def chat_stream(self, messages: list[dict], model: str,
                    temperature: float,
                    tools: list[dict] | None = None): ...  # Iterator[LLMChunk]
```

**配置：**
```yaml
# .env
LLM_PROVIDER=openai          # openai | modelscope | zhipu | ollama | vllm | 自定义
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1  # 可选，Provider 有默认值
```

**工厂模式（内嵌在 AgentLLM 构造函数中）：**
```python
class AgentLLM:
    _registry = LLMProviderRegistry()

    @classmethod
    def register_provider(cls, name: str, provider: LLMProvider): ...

    def __init__(self, provider=None, model=None, ...):
        # 1. 读取 LLM_PROVIDER → 2. 查 PROVIDER_CONFIG → 3. 获取/注册 Provider
        ...

    def invoke(self, messages: list[dict], temperature=None,
               tools: list[dict] | None = None,
               tool_choice: str | dict | None = None, **kwargs) -> LLMResponse: ...
    def stream(self, messages: list[dict], temperature=None,
               tools: list[dict] | None = None, **kwargs): ...  # Iterator[LLMChunk]
```

**Provider 配置字典（`PROVIDER_CONFIG`）：**

```python
PROVIDER_CONFIG: dict[str, dict] = {
    "openai": {
        "class": "kagent.core.llm.OpenAIProvider",
        "default_base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "env_base_url": "OPENAI_BASE_URL",
    },
    "modelscope": {
        "class": "kagent.core.llm.ModelScopeProvider",
        "default_base_url": "https://api-inference.modelscope.cn/v1",
        "env_key": "MODELSCOPE_API_KEY",
    },
    "zhipu": {
        "class": "kagent.core.llm.ZhipuProvider",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "env_key": "ZHIPU_API_KEY",
    },
    "ollama": {
        "class": "kagent.core.llm.OllamaProvider",
        "default_base_url": "http://localhost:11434/v1",
        "env_key": None,  # Ollama 无需 API Key
    },
    "vllm": {
        "class": "kagent.core.llm.VLLMProvider",
        "default_base_url": "http://localhost:8000/v1",
        "env_key": None,
    },
}
# 初始化流程：查 PROVIDER_CONFIG[name] → 读 env_key 取凭证 → 实例化 provider class → register
```

**降级策略**：Provider 不可用时抛出 `LLMError`，Agent 层捕获后记录 Trace 并终止。

#### 3.1.2 LLMProviderRegistry

**接口定义：**
```python
class LLMProviderRegistry:
    def register(self, name: str, provider: LLMProvider) -> None: ...
    def get(self, name: str) -> LLMProvider: ...           # 不存在抛 ValueError
    def list_providers(self) -> list[str]: ...
```

### 3.2 工具系统

#### 3.2.1 Tool

**接口定义：**
```python
class ToolResult(BaseModel):
    content: str
    success: bool = True
    error: str | None = None
    metadata: dict = Field(default_factory=dict)

class ToolParameter(BaseModel):
    name: str
    type: str           # "string" | "number" | "boolean" | "array"
    description: str
    required: bool = True
    default: Any = None

class Tool(ABC):
    def __init__(self, name: str, description: str): ...
    @abstractmethod
    def run(self, parameters: dict) -> ToolResult: ...
    @abstractmethod
    def get_parameters(self) -> list[ToolParameter]: ...
    def to_openai_schema(self) -> dict: ...  # 用于 FunctionCallAgent
```

**配置：**
```yaml
# settings.yaml
tools:
  builtin:
    - calculator
    - search
  mcp_servers:
    - command: ["python", "my_rag_server.py"]
      name: rag
```

**工厂模式：**
```python
class ToolRegistry:
    def register_tool(self, tool: Tool) -> None: ...       # 方式一
    def register_function(self, name, desc, func) -> None: ...  # 方式二
    def unregister(self, name: str) -> bool: ...
    def execute_tool(self, name: str, arguments: dict) -> ToolResult: ...
    def get_tools_description(self) -> str: ...             # 注入 Prompt
    # register_mcp() 在 D6 阶段新增，此时 MCPTool 尚不存在
```

**降级策略（统一约束）**：
- **工具执行异常**：`execute_tool()` 内部 try/except 包裹，永远返回 `ToolResult(success=False, error=..., content="[ERROR] 工具 '{name}' 执行失败: {message}")`，**不抛异常**，不中断 Agent 循环。Trace 记录 `SpanStatus.ERROR` + 携带 `user_message`。
- **LLM API 超时/限流**：指数退避重试（1s→2s→4s，最多 3 次）。3 次均失败后抛 `LLMError`（含 `user_message`），由 Agent 层捕获并终止。
- **搜索幂等**：同一 query 5s 内走缓存，不发起重复 HTTP 请求。

### 3.3 MCP 外部网关

#### 3.3.1 MCPTool

**接口定义：**
```python
class MCPTool:
    def __init__(self, server_command: list[str]): ...
    def discover_tools(self) -> list[Tool]: ...   # 调用 tools/list 自动发现
    def call_tool(self, name: str, arguments: dict) -> ToolResult: ...
```

**配置：**
```yaml
mcp:
  servers:
    - name: rag
      command: ["python", "my_rag_project/server.py"]
    - name: github
      command: ["npx", "-y", "@modelcontextprotocol/server-github"]
```

### 3.4 链路追踪

#### 3.4.1 Tracer + Span

**接口定义：**
```python
class SpanType(str, Enum):
    AGENT_RUN = "agent.run"
    AGENT_STEP = "agent.step"
    LLM_CALL = "llm.call"
    TOOL_CALL = "tool.call"

class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"

@dataclass
class Span:
    name: str; type: SpanType; trace_id: str; span_id: str
    parent_id: str | None = None; start_time: float = 0.0; end_time: float | None = None
    duration_ms: float | None = None; input: str | None = None; output: str | None = None
    status: SpanStatus = SpanStatus.OK; error: str | None = None
    metadata: dict = field(default_factory=dict)   # ⚠️ Python 可变默认值陷阱！必须用 default_factory
    children: list["Span"] = field(default_factory=list)

class Tracer:
    """单例"""
    def start_trace(self, name, input_text="") -> Span: ...
    def start_span(self, name, type, input_data="", **metadata) -> Span: ...
    def end_span(self, span, output="", status=SpanStatus.OK, error="") -> Span: ...
    @contextmanager
    def span(self, name, type, **metadata): ...  # Context Manager
    def add_event(self, name: str, data: dict) -> None: ...  # 向当前活跃 Span 注入事件（"llm.start"/"llm.end"/"tool.start"/"tool.end"/"error"/"retry"）
    def get_current_trace(self) -> Span | None: ...
    def get_all_traces(self) -> list[Span]: ...
    def clear(self) -> None: ...  # 清空所有 traces

class TraceExporter:
    @staticmethod def to_dict(span) -> dict: ...
    @staticmethod def to_json(span, indent=2) -> str: ...
    @staticmethod def to_tree(span, indent=0) -> str: ...
```

### 3.5 Agent 抽象基类

```python
class Agent(ABC):
    def __init__(self, name, llm: AgentLLM, system_prompt=None, config=None,
                 custom_prompt: str | None = None): ...
    """custom_prompt 模板变量（所有 Agent 子类统一支持）：
       {tools}       — 工具列表描述（由 ToolRegistry.get_tools_description() 生成）
       {history}     — 历史消息（Message.to_dict() 格式化）
       {input}       — 当前用户输入
       {max_steps}   — 最大步数
       Agent 子类可追加自己的变量（ReActAgent 加 {thought_format} 等）。
    """
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str: ...
    def add_message(self, message: Message): ...
    def clear_history(self): ...
    def get_history(self) -> list[Message]: ...
```

### 3.6 消息系统 + 配置 + 异常

```python
class Message(BaseModel):
    content: str; role: Literal["user","assistant","system","tool"]
    timestamp: datetime; metadata: dict | None
    def to_dict(self) -> dict: ...

class Config(BaseModel):
    default_model: str; default_provider: str; temperature: float
    max_tokens: int | None; debug: bool; log_level: str; max_history_length: int
    @classmethod def from_env(cls) -> "Config": ...

class KagentError(Exception):
    def __init__(self, user_message: str, debug_message: str | None = None): ...
class AgentError(KagentError): ...
class LLMError(KagentError): ...
class ToolError(KagentError): ...
class ConfigError(KagentError): ...
```

### 3.7 运行时约束与安全模型

#### 3.7.1 并发与上下文隔离

- `Tracer` 使用 `contextvars` 保存当前 trace，避免多线程或 async Agent 并发运行时串 trace。
- `Registry` 的运行时热插拔只影响新建 Agent 或下一次 `run()`，不修改正在执行中的调用链。
- `ToolRegistry` 注册 / 注销操作需要加锁；工具执行阶段读取不可变快照，避免执行中工具集合变化。
- v0.1 默认同步接口优先；async 工具执行器放入后续版本，避免第一版接口复杂化。

#### 3.7.2 安全与隐私

- Trace / 日志默认脱敏：API Key、Authorization、Cookie、password、secret、token 等字段不得明文写入。
- `LLMResponse.raw` 和 `ToolResult.metadata` 默认不导出到 JSON；只有 `debug=True` 且显式允许时才导出。
- `TerminalTool` 默认只允许 `read/list`，并限制在配置的 workspace 根目录内；写入、删除、执行命令必须作为后续高级能力单独开启。
- 外部工具默认 allowlist 注册，禁止从配置中静默启用未知危险工具。
- 用户可见错误使用 `user_message`，开发者调试信息使用 `debug_message`，避免把内部路径、密钥、HTTP 原文暴露给最终用户。

---

## 4. 测试方案

### 4.1 TDD 哲学

先写测试 → 测试失败 → 实现 → 测试通过 → 重构。每个 ~1h 任务必须包含 `Test Method` 条目。

### 4.2 测试分层

```
        /\
       /E2E\           ← F1-F3：实战项目完整链路
      /------\
     /集成测试 \        ← Agent+Tool / Agent+Tracing / MCP 集成
    /----------\
   /  单元测试   \      ← 每个类/函数的独立验证
  /______________\
```

---

### 4.3 阶段 A 测试用例（LLM + Tool 可插拔）

#### 单元测试

| 测试文件 | 测试函数 | 验证内容 | Mock 策略 |
|---------|---------|---------|----------|
| `tests/unit/test_config.py` | `test_config_from_env` | `.env` 字段正确映射到 Config | 临时设置环境变量 |
| | `test_config_missing_api_key` | 缺 `LLM_API_KEY` 时 `from_env()` 抛 `ConfigError` | `monkeypatch.delenv` |
| | `test_config_default_values` | 未设置时使用 `Config` 默认值 | monkeypatch |
| `tests/unit/test_llm.py` | `test_provider_is_abstract` | `LLMProvider()` 抛 `TypeError` | 无 |
| | `test_registry_register_and_get` | 注册 → 获取 → 类型正确 | Mock `LLMProvider` |
| | `test_registry_get_nonexistent` | `get("unknown")` 抛 `ValueError` | 无 |
| | `test_registry_list_providers` | 注册 2 个 → `list_providers()` 返回 2 个 | Mock |
| | `test_agent_llm_init_from_env` | `AgentLLM()` 从 `LLM_PROVIDER` 读取 provider | Mock `OpenAIProvider` |
| | `test_agent_llm_explicit_provider` | `AgentLLM(provider="ollama")` 优先于 env | Mock |
| | `test_agent_llm_register_custom` | `AgentLLM.register_provider("x", mock)` → `AgentLLM(provider="x")` 可用 | Mock |
| | `test_agent_llm_missing_provider` | `LLM_PROVIDER=unknown` 时抛 `ConfigError` | monkeypatch |
| | `test_openai_provider_chat` | `chat()` 返回非空字符串 | Mock `OpenAI.chat.completions.create` |
| | `test_openai_provider_chat_stream` | `chat_stream()` yield 多个 chunk | Mock |
| | `test_openai_provider_timeout` | API 超时 → `LLMError` | Mock `httpx.TimeoutException` |
| `tests/unit/test_tools.py` | `test_tool_is_abstract` | `Tool()` 抛 `TypeError` | 无 |
| | `test_tool_parameter_required` | `ToolParameter(required=True)` 缺省值 | 无 |
| | `test_registry_register_tool` | `register_tool(tool)` → `execute_tool(name, arguments)` 返回 `ToolResult(success=True)` | 真实 Tool 子类 |
| | `test_registry_register_function` | `register_function("echo", desc, lambda x: x)` → 执行返回 `"x"` | 真实函数 |
| | `test_registry_unregister` | `unregister("x")` 后 `execute_tool("x", ...)` 返回 `ToolResult(success=False)` | 无 |
| | `test_registry_get_tools_description` | 注册 2 个工具 → description 字符串含两个工具名 | 真实 |
| | `test_calculator_basic_ops` | `"2+3*4"` → `"14"` / `"sqrt(16)"` → `"4.0"` / `"10/3"` → 浮点 | 真实 `CalculatorTool` |
| | `test_calculator_invalid_expr` | `"1/0"` → 返回错误字符串，不抛异常 | 真实 |
| | `test_calculator_empty_input` | `""` → `"表达式不能为空"` | 真实 |
| | `test_search_real` | `search({"query": "Python"})` 返回非空（需 API Key） | 真实 API（可 skip） |
| | `test_search_no_api_key` | 未配置 API Key → 返回配置提示字符串 | monkeypatch |

#### 集成测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/integration/test_llm_tool_wire.py` | `test_agent_llm_with_registry` | AgentLLM 初始化 → ToolRegistry 注入 Agent → 运行 |
| | `test_provider_switch_at_runtime` | `.env` 改 `LLM_PROVIDER` → 重建 AgentLLM → 不同 Provider |

---

### 4.4 阶段 B 测试用例（Agent 范式）

#### 单元测试

| 测试文件 | 测试函数 | 验证内容 | Mock 策略 |
|---------|---------|---------|----------|
| `tests/unit/test_message.py` | `test_message_create` | `Message("hi", "user")` → `role=="user"`, `content=="hi"` | 无 |
| | `test_message_to_dict` | `to_dict()` 返回 `{"role":"user","content":"hi"}` | 无 |
| | `test_message_timestamp_auto` | 未传 timestamp → 自动设为当前时间 | 无 |
| `tests/unit/test_agent.py` | `test_agent_is_abstract` | `Agent()` 抛 `TypeError` | 无 |
| | `test_agent_history` | `add_message()` → `get_history()` 包含新消息 | Mock Agent 子类 |
| | `test_agent_clear_history` | 添加 3 条 → `clear_history()` → `get_history()` 为空 | Mock |
| | `test_simple_agent_no_tools` | Mock LLM → `run("hi")` 返回 Mock 响应 | Mock `AgentLLM` |
| | `test_simple_agent_with_tools` | LLM 返回 `[TOOL_CALL:calc:1+1]` → 解析 → 执行 → 二次调用 LLM | Mock LLM + 真实 CalculatorTool |
| | `test_simple_agent_parse_tool_calls` | `"[TOOL_CALL:calc:1+1]"` → `[{tool_name:"calc", params:"1+1"}]` | 无 |
| | `test_react_agent_finish` | Mock LLM 返回 `Action: Finish[答案]` → `run()` 立即返回 `"答案"` | Mock |
| | `test_react_agent_parse_thought_action` | 解析标准格式 → `(thought, action)` 均非 None | 真实解析函数 |
| | `test_react_agent_malformed_action` | LLM 返回无 `Action:` → history 注入错误 → 继续循环 | Mock |
| | `test_react_agent_max_steps` | `max_steps=2` → LLM 一直不 Finish → 2 步后终止 | Mock |
| | `test_plan_solve_plan_parse` | LLM 返回 `["步骤1","步骤2"]` → `ast.literal_eval` 解析成功 | Mock |
| | `test_plan_solve_execute_steps` | 2 步计划 → LLM 分步返回 → 最终结果正确 | Mock |
| | `test_plan_solve_bad_plan_format` | LLM 返回非列表 → 抛 `AgentError` | Mock |
| | `test_reflection_converge` | 第 1 轮 reflect 返回 `无需改进` → 只运行 1 轮 | Mock |
| | `test_reflection_max_steps` | reflect 一直不收敛 → `max_steps=2` 后强制返回 | Mock |
| | `test_function_call_tool_choice_auto` | `tool_choice="auto"` → LLM 返回 `tool_calls` → 执行 → 二次调用 | Mock OpenAI |
| | `test_function_call_parallel_tools` | LLM 返回 2 个 tool_calls → 并行执行 → 结果注入 | Mock |
| | `test_function_call_tool_timeout` | 工具执行超时 → 返回超时错误 → 不中断循环 | Mock |
| | `test_function_call_nonexistent_tool` | LLM 调用不存在的工具 → 返回错误 → LLM 可选其他工具 | Mock |

#### 集成测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/integration/test_agent_with_tool.py` | `test_react_agent_search_integration` | 真实 LLM + 真实 SearchTool → 回答实时问题 |
| | `test_simple_agent_calculator_integration` | 真实 LLM + CalculatorTool → 正确计算结果 |
| | `test_function_call_agent_integration` | 真实 LLM（支持 function calling）+ 2 个工具 → 选对工具 |
| `tests/integration/test_agent_multi_tool.py` | `test_react_agent_uses_correct_tool` | 给 Search + Calculator → "算 1+1" 应调用 Calculator |
| | `test_react_agent_tool_chain` | 需要先搜索再计算 → 两步分别调用不同工具 |

---

### 4.5 阶段 C 测试用例（框架化）

#### 单元测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/unit/test_config.py` | `test_config_pydantic_validation` | Config 参数类型不对 → Pydantic 抛 `ValidationError` |
| | `test_config_to_dict` | `Config().to_dict()` 返回完整字典 |
| `tests/unit/test_exceptions.py` | `test_kagent_error_inheritance` | `AgentError` / `LLMError` / `ToolError` / `ConfigError` 都是 `KagentError` 子类 |
| | `test_error_user_message` | `KagentError(user_message="用户消息", debug_message="调试")` 双字段存在 |
| `tests/unit/test_agent.py` | `test_react_agent_custom_prompt` | `custom_prompt="{tools}\n{input}"` → 生成的 Prompt 包含 `{tools}` 展开后的工具描述 |
| | `test_agent_config_propagation` | Agent 的 `config.temperature` 传递到 LLM 调用 |

#### 集成测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/integration/test_framework_import.py` | `test_all_exports` | `from kagent import SimpleAgent, ReActAgent, ...` 全部可用 |
| `tests/integration/test_pip_install.py` | `test_editable_install` | `pip install -e .` 后 import 成功 |

---

### 4.6 阶段 D 测试用例（追踪 + MCP + 容错 + 监控）

#### 单元测试

| 测试文件 | 测试函数 | 验证内容 | Mock 策略 |
|---------|---------|---------|----------|
| `tests/unit/test_tracing.py` | `test_span_creation` | `Span(name, SpanType.AGENT_RUN, trace_id)` 创建成功，`span_id` 自动生成 | 无 |
| | `test_tracer_singleton` | `Tracer()` 两次调用返回同一实例 | 无 |
| | `test_tracer_start_trace` | `start_trace("test", "input")` → 返回根 Span，`parent_id=None` | 无 |
| | `test_tracer_start_span` | 在 trace 中 `start_span("step", AGENT_STEP)` → `parent_id` 指向根 | 无 |
| | `test_tracer_span_tree` | trace→step→llm→tool 4 层嵌套 → children 树正确 | 顺序调用 |
| | `test_tracer_context_manager` | `with tracer.span(...) as s:` → 自动 end_span → `duration_ms` 非空 | 无 |
| | `test_tracer_context_manager_error` | Context manager 内抛异常 → Span `status=ERROR` + `error` 字段 | 主动抛异常 |
| | `test_tracer_without_trace` | 未 `start_trace` 调 `start_span` → `RuntimeError` | 无 |
| | `test_tracer_clear` | 多次 trace → `clear()` → `get_all_traces()` 空 | 无 |
| | `test_exporter_to_dict` | Span 树 → `to_dict()` 包含所有字段 + children 递归 | 无 |
| | `test_exporter_to_json` | `to_json()` 输出可 `json.loads` 还原 | 无 |
| | `test_exporter_to_tree` | `to_tree()` 字符串包含 span name + `duration_ms` + `├──` | 无 |
| | `test_tracer_token_stats` | `add_event("llm.end", {"token_usage":...})` → `to_json` 顶层汇总 | 无 |
| `tests/unit/test_fault_tolerance.py` | `test_tool_error_returns_string` | Tool 抛 `ValueError` → `execute_tool` 返回 `"[ERROR] ..."` 不抛异常 | Mock Tool |
| | `test_mcp_auto_reconnect` | MCP 子进程断开 → `call_tool` 重连成功 → 返回结果 | Mock subprocess |
| | `test_mcp_reconnect_exhausted` | 3 次重连失败 → `ToolError` 含 `user_message` | Mock |
| | `test_llm_retry_backoff` | API 返回 429 → 1s/2s/4s 重试 → 3 次后抛 `LLMError` | Mock `httpx.Response(429)` |
| | `test_search_idempotent_cache` | 相同 query 5s 内 2 次调用 → 第二次从缓存返回 → API 只调用 1 次 | Mock API |

#### 集成测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/integration/test_agent_with_tracing.py` | `test_react_agent_has_full_trace` | 跑完整 Agent → Trace 树含 `AGENT_RUN/AGENT_STEP/LLM_CALL/TOOL_CALL` |
| | `test_trace_contains_token_stats` | Trace JSON 顶层 `total_tokens.prompt > 0` |
| | `test_trace_error_on_tool_failure` | 工具损坏 → Span status=ERROR → 循环继续 |
| `tests/integration/test_mcp.py` | `test_mcp_connect_and_discover` | 启动 MCP Server → MCPTool 连接 → `discover_tools()` 返回工具列表 |
| | `test_mcp_call_tool` | `call_tool("search_docs", {"query":"test"})` → 返回非空 |
| | `test_mcp_tool_in_registry` | `registry.register_mcp(mcp)` → ToolRegistry 可执行 MCP 工具 |
| | `test_mcp_server_crash_recovery` | kill MCP 进程 → Agent 下次调用 → 自动重连 |

---

### 4.7 阶段 E 测试用例（记忆 + 上下文）

#### 单元测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/unit/test_memory.py` | `test_base_memory_is_abstract` | `BaseMemory()` 抛 `TypeError` |
| | `test_working_memory_store_recall` | `store(item)` → `search("key", top_k=1)` 返回 item |
| | `test_working_memory_ttl` | TTL 超时 → `search` 不再返回该 item |
| | `test_working_memory_capacity` | 超过容量 → 淘汰最旧的 item |
| | `test_episodic_memory_timeline` | 3 个事件按时间存储 → 按时间范围检索返回正确事件 |
| | `test_memory_manager_multi_backend` | Manager 注册 Working+Episodic → `search` 返回两个来源结果 |
| | `test_memory_tool_recall` | Agent 调 `[TOOL_CALL:memory:action=recall,query=...]` → 返回匹配记忆 |
| `tests/unit/test_context.py` | `test_context_builder_gather` | 输入 messages → `gather()` 返回 Context 对象 |
| | `test_context_builder_compress` | 2000 tokens → `compress(max_tokens=500)` → 输出 ≤ 500 tokens |
| | `test_context_builder_gscc_pipeline` | `build(messages, tools_results)` → 完整流水线输出非空 |
| `tests/unit/test_note_terminal.py` | `test_note_tool_crud` | 创建→读取→更新→删除 笔记 |
| | `test_terminal_tool_list` | `TerminalTool({"action":"list", "path":"."})` → 返回文件列表 |

#### 集成测试

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/integration/test_memory_tool.py` | `test_agent_remembers_user_fact` | 对话 1 "我叫张三" → 对话 2 "你是谁" → 回答含 "张三" |
| | `test_agent_forgets_on_clear` | 存储 → `clear_history` → 再次问 → 不记得 |
| `tests/integration/test_context.py` | `test_long_conversation_compression` | 50 轮对话 → build 后 token 数 ≤ max_tokens |

---

### 4.8 阶段 F 测试用例（E2E 验收）

| 测试文件 | 测试函数 | 验证内容 |
|---------|---------|---------|
| `tests/e2e/test_react_agent.py` | `test_search_weather_and_calculate` | "查北京天气，算华氏度" → 调用 Search + Calculator → 答案含温度 |
| | `test_react_agent_handles_error` | 搜索工具损坏 → Agent 返回 "无法完成" 而非崩溃 |
| `tests/e2e/test_plan_solve.py` | `test_multi_step_math` | 多步数学题 → 生成计划 → 逐步执行 → 正确答案 |
| `tests/e2e/test_reflection.py` | `test_code_optimization` | "写素筛函数" → 初版试除法 → 反思后优化为筛法 |
| `tests/e2e/test_function_call.py` | `test_parallel_tool_calls` | "同时查北京和上海天气" → 并行调 2 次 Search → 2 个结果 |
| `tests/e2e/test_provider_switch.py` | `test_switch_provider_same_behavior` | 同问题 → openai / ollama → 两次都成功且答案合理 |

---

### 4.9 质量指标

| 类别 | 指标 | 目标 |
|------|------|------|
| 单元测试 | 覆盖率 | >= 80% |
| 单元测试 | 总用例数 | >= 55 |
| 集成测试 | 关键路径覆盖率 | 100%（所有集成场景） |
| 集成测试 | 总用例数 | >= 15 |
| E2E | 核心场景 | >= 6 个场景通过 |
| CI | 全量测试耗时 | < 5 分钟（不含真实 LLM 调用的测试） |

### 4.10 测试可复现性约束

- 单元测试必须默认离线运行，不依赖真实 LLM、真实搜索 API、真实天气结果。
- 真实 Provider / SearchTool / MCP Server 测试统一标记为 `pytest.mark.external`，CI 默认跳过。
- 涉及“今天”“天气”“实时搜索”的黄金用例只校验工具调用路径与结构化结果，不校验自然语言答案的固定文本。
- E2E 测试允许使用录制响应或 Mock Provider，真实服务 smoke test 只作为发布前手动检查。

### 4.11 黄金测试集

> **定位**：这是一组**发布前手动 smoke test checklist**，不是 CI 自动化测试。每个条目代表一个真实端到端用户场景，测试人员按顺序执行并记录结果。断言策略：`easy` 条目精确匹配 `expected_value`；`medium/hard` 条目只验证结构化路径（工具调用链、步数），不验证自然语言答案的固定文本。
> 
> CI 自动化测试（4.3-4.8）覆盖离线的单元/集成/E2E；黄金测试集用真实 LLM + 真实 API 做发布前终检。

```json
[
  {"input": "1+1=?", "expected_type": "numeric_answer", "expected_value": "2",
   "agent": "SimpleAgent", "tool": "CalculatorTool", "difficulty": "easy"},

  {"input": "今天北京的天气怎么样？", "expected_type": "search_answer",
   "agent": "ReActAgent", "tool": "SearchTool", "difficulty": "easy"},

  {"input": "查一下北京和上海的天气，哪个城市更热？", "expected_type": "multi_tool",
   "agent": "ReActAgent", "tools": ["SearchTool"], "min_steps": 2, "difficulty": "medium"},

  {"input": "查北京天气，算 25°C 等于多少华氏度", "expected_type": "tool_chain",
   "agent": "ReActAgent", "tools": ["SearchTool", "CalculatorTool"],
   "min_steps": 2, "difficulty": "medium"},

  {"input": "写出一个 Python 快速排序函数", "expected_type": "code",
   "agent": "ReflectionAgent", "difficulty": "medium"},

  {"input": "同时查北京、上海、深圳的天气", "expected_type": "parallel_tools",
   "agent": "FunctionCallAgent", "tool_count": 3, "difficulty": "hard"}
]
```

---

## 5. 系统架构与模块设计

### 5.1 架构图

```
                        ┌──────────────────────────────────────┐
                        │           👤 用户代码                  │
                        │    agent = ReActAgent(llm, tools)     │
                        │    agent.run("帮我查天气并计算...")    │
                        └────────────────┬─────────────────────┘
                                         │
                        ┌────────────────▼─────────────────────┐
                        │         🧠 Agent API 层               │
                        │                                      │
                        │  SimpleAgent  │  ReActAgent           │
                        │               │                      │
                        │  ★ v0.1 MVP   │  ★ v0.1 MVP          │
                        │───────────────┼───────────────────────│
                        │  PlanSolve / Reflect / FunctionCall   │
                        │  → v0.2+                             │
                        │  自定义 Agent (继承 Agent 基类)        │
                        └────────┬───────────┬─────────────────┘
                                 │           │
              ┌──────────────────┼───────────┼──────────────────┐
              │                  │           │                  │
              │    ┌─────────────▼──┐  ┌─────▼──────────────┐  │
              │    │   AgentLLM     │  │   ToolRegistry     │  │
              │    │  (LLM 门面)    │  │  (工具注册中心)     │  │
              │    │                │  │                    │  │
              │    │ .invoke()      │  │ .register_tool()   │  │
              │    │ .stream()      │  │ .register_function()│  │
              │    │                │  │ .unregister()      │  │      🔌 可插拔层
              │    │                │  │ .execute_tool()    │  │
              │    └───────┬────────┘  └──────┬─────────────┘  │
              │            │                  │                │
              │            │         ┌────────┼────────┐       │
              │            │         │        │        │       │
              │    ┌───────▼──┐  ┌───▼──┐ ┌──▼──┐           │
              │    │Provider  │  │Tool  │ │裸函 │            │
              │    │Registry  │  │对象  │ │注册  │            │
              │    └───────┬──┘  └───┬──┘ └──┬──┘           │
              │            │         │       │                │
              └────────────┼─────────┼───────┼────────────────┘
                           │         │       │       │
        ┌──────────────────┼─────────┼───────┼───────┼──────────────────┐
        │                  │         │       │       │                  │
        │                  │         │       │                │
        │  ┌──────┐  ┌────▼──┐ ┌───▼──────┐   ⚙️ 实现层     │              │
        │  │.env  │  │OpenAI │ │Calc+Search│                 │
        │  │配置  │  │Provider│ │内置 Tool  │  ★ v0.1 MVP    │
        │  └──────┘  └───────┘ └──────────┘                 │
        │                                                   │
        │  v0.2+: Ollama/VLLM/Zhipu/ModelScope Provider     │
        │  v0.3+: MCPTool + MCP Server 外部网关              │
        └───────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────────────────────┐
        │        🧱 基础设施层 + MCP 外部网关 (v0.3+)                    │
        │                                                              │
        │  Memory System / ContextBuilder / Storage → 后续版本          │
        └──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      🔍 横切关注层（贯穿所有层）                                │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  ★ 链路追踪   │  │   监控告警    │  │   容错降级    │  │   配置驱动    │    │
│  │              │  │              │  │              │  │              │    │
│  │ Tracer 单例  │  │ trace_id 贯穿 │  │ try/except   │  │ .env +       │    │
│  │ Span 树      │  │ Token 统计   │  │ 指数退避重试  │  │ settings.yaml│    │
│  │ Tree/JSON导出│  │ 请求级日志   │  │ 幂等+缓存    │  │ 一行切换     │    │
│  │              │  │              │  │              │  │              │    │
│  │ ★ v0.1 核心  │  │   v0.3+      │  │   v0.3+      │  │   v0.1       │    │
│  └──────┬───────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                                                                    │
│         │  Tracer 埋点在 Agent.run() / AgentLLM.invoke() /                   │
│         │  ToolRegistry.execute_tool() 中自动调用，零配置                     │
│         └────────────────────────────────────────────────────────────────────│
└─────────────────────────────────────────────────────────────────────────────┘

### 5.2 目录结构

```
kagent/                              # ★ = v0.1 MVP 文件
├── config/
│   └── settings.yaml
├── kagent/
│   ├── core/
│   │   ├── __init__.py              ★
│   │   ├── config.py                ★ Config 类
│   │   ├── exceptions.py            ★ KagentError / AgentError / LLMError / ToolError / ConfigError
│   │   ├── llm/                     ★ LLM 调用层（可插拔注册制）
│   │   │   ├── __init__.py          ★ 统一导出
│   │   │   ├── models.py            ★ LLMResponse + LLMChunk
│   │   │   ├── base.py              ★ LLMProvider(ABC) + LLMProviderRegistry
│   │   │   ├── factory.py           ★ AgentLLM + PROVIDER_CONFIG
│   │   │   └── providers.py         ★ OpenAIProvider（可插拔实现）
│   │   ├── agent/                   ★ Agent 基类 + Message 系统
│   │   │   ├── __init__.py          ★
│   │   │   ├── base.py              ★ Agent(ABC)
│   │   │   └── message.py           ★ Message 类
│   │   └── tracing/                 ★ 链路追踪
│   │       ├── __init__.py          ★
│   │       ├── models.py            ★ Span + SpanType + SpanStatus
│   │       ├── tracer.py            ★ Tracer 单例
│   │       └── exporter.py          ★ TraceExporter
│   ├── agents/
│   │   ├── __init__.py              ★
│   │   ├── simple_agent.py          ★ SimpleAgent
│   │   ├── react_agent.py           ★ ReActAgent
│   │   ├── reflection_agent.py      (v0.2+)
│   │   ├── plan_solve_agent.py      (v0.2+)
│   │   └── function_call_agent.py   (v0.2+)
│   ├── tools/
│   │   ├── __init__.py              ★
│   │   ├── base.py                  ★ Tool + ToolParameter + ToolResult
│   │   ├── registry.py              ★ ToolRegistry
│   │   ├── mcp_tool.py              (v0.3+)
│   │   └── builtin/
│   │       ├── __init__.py          ★
│   │       ├── calculator.py        ★ CalculatorTool
│   │       └── search.py            ★ SearchTool
│   ├── memory/                      (v0.4+, 目录预留)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── manager.py
│   │   ├── working.py
│   │   ├── episodic.py
│   │   ├── semantic.py
│   │   └── tool.py
│   ├── context/                     (v0.4+, 目录预留)
│   │   ├── __init__.py
│   │   └── builder.py
│   └── __init__.py                  ★
├── tests/
│   ├── unit/
│   │   ├── test_llm.py              ★
│   │   ├── test_tools.py            ★
│   │   ├── test_tracing.py          ★
│   │   ├── test_agent.py            ★
│   │   ├── test_message.py          ★
│   │   ├── test_config.py           ★
│   │   ├── test_exceptions.py       ★
│   │   ├── test_memory.py           (v0.4+)
│   │   ├── test_context.py          (v0.4+)
│   │   ├── test_note_terminal.py    (v0.4+)
│   │   └── test_fault_tolerance.py  (v0.3+)
│   ├── integration/
│   │   ├── test_agent_with_tool.py  ★
│   │   ├── test_agent_with_tracing.py ★
│   │   ├── test_llm_tool_wire.py    ★
│   │   ├── test_framework_import.py ★ (C8)
│   │   ├── test_mcp.py              (v0.3+)
│   │   ├── test_memory_tool.py      (v0.4+)
│   │   ├── test_context.py          (v0.4+)
│   │   └── test_pip_install.py      ★ (C8)
│   ├── e2e/
│   │   └── test_react_agent.py      (手动, 真实 LLM)
│   └── fixtures/
│       └── .env.test                ★
├── pyproject.toml                   ★
├── requirements.txt                 ★ 核心依赖（开源用户 pip install -r requirements.txt）
├── requirements-dev.txt             ★ 开发依赖（-r requirements.txt + pytest）
├── .env.example                     ★
├── .gitignore                       ★ (.venv/, .env, __pycache__/, *.egg-info/)
└── README.md                        ★
```

### 5.3 数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│                     一次 ReActAgent.run() 调用                        │
└─────────────────────────────────────────────────────────────────────┘

 用户: "帮我查一下北京天气，然后算一下 25°C 等于多少华氏度"

   │
   ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  Tracer.start_trace("ReActAgent.run", input)                     │
 │  → trace_id = "a1b2c3d4"                                        │
 │  → run_id   = "x9y8z7w6"                                        │
 └──────────────────────────────────────────────────────────────────┘
   │
   ▼
 ╔══════════════════════════════════════════════════════════════════╗
 ║  Step 1                                                         ║
 ║  ┌──────────────────────────────────────────────────────────┐   ║
 ║  │ 1. 构建 Prompt                                           │   ║
 ║  │    工具列表: Search, Calculator                          │   ║
 ║  │    问题: 北京天气 + 温度转换                             │   ║
 ║  │    历史: (空)                                            │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ║     │                                                           ║
 ║  ┌──▼──────────────────────────────────────────────────────┐   ║
 ║  │ 2. Tracer.start_span("llm.call.step1", LLM_CALL)        │   ║
 ║  │    AgentLLM.invoke(messages) ──→ OpenAI API              │   ║
 ║  │    ← 返回: "Thought: 需要查天气...                      │   ║
 ║  │             Action: Search[北京今日天气]"                │   ║
 ║  │    metadata: {token_usage: {prompt: 320, comp: 85}}     │   ║
 ║  │    Tracer.end_span(llm_span, duration_ms: 1230)          │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ║     │                                                           ║
 ║  ┌──▼──────────────────────────────────────────────────────┐   ║
 ║  │ 3. 正则解析 Thought / Action                            │   ║
 ║  │    格式: "Thought: ...\nAction: ToolName[params]"       │   ║
 ║  │    → thought="需要查天气信息"                            │   ║
 ║  │    → tool_name="Search", tool_input="北京今日天气"       │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ║     │                                                           ║
 ║  ┌──▼──────────────────────────────────────────────────────┐   ║
 ║  │ 4. Tracer.start_span("tool.call.Search", TOOL_CALL)     │   ║
 ║  │    ToolRegistry.execute_tool("Search", {"query":        │   ║
 ║  │        "北京今日天气"})                                  │   ║
 ║  │    ← ToolResult(success=True,                           │   ║
 ║  │        content="北京晴, 25°C, 湿度40%")                 │   ║
 ║  │    Tracer.end_span(tool_span, duration_ms: 450)         │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ║     │                                                           ║
 ║  ┌──▼──────────────────────────────────────────────────────┐   ║
 ║  │ 5. 注入历史: Action: Search[北京今日天气]                 │   ║
 ║  │             Observation: 北京晴, 25°C, 湿度40%           │   ║
 ║  │    Tracer.end_span(step_span)                           │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ╚══════════════════════════════════════════════════════════════════╝
   │
   ▼
 ╔══════════════════════════════════════════════════════════════════╗
 ║  Step 2                                                         ║
 ║  ┌──────────────────────────────────────────────────────────┐   ║
 ║  │ 1. 构建 Prompt（含历史）                                 │   ║
 ║  │ 2. Tracer.start_span("llm.call.step2", LLM_CALL)        │   ║
 ║  │    AgentLLM.invoke() ──→                                 │   ║
 ║  │    ← "Thought: 天气已查到，需要转换温度                  │   ║
 ║  │        Action: Calculator[25 * 9/5 + 32]"               │   ║
 ║  │    Tracer.end_span(llm_span, duration_ms: 890)           │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ║     │                                                           ║
 ║  ┌──▼──────────────────────────────────────────────────────┐   ║
 ║  │ 3. Tracer.start_span("tool.call.Calculator", TOOL_CALL) │   ║
 ║  │    ToolRegistry.execute_tool("Calculator",               │   ║
 ║  │        {"expression": "25 * 9/5 + 32"})                 │   ║
 ║  │    ← ToolResult(success=True, content="77.0")            │   ║
 ║  │    Tracer.end_span(tool_span, duration_ms: 15)           │   ║
 ║  └──────────────────────────────────────────────────────────┘   ║
 ╚══════════════════════════════════════════════════════════════════╝
   │
   ▼
 ╔══════════════════════════════════════════════════════════════════╗
 ║  Step 3                                                         ║
 ║    LLM 返回: "Action: Finish[北京今天晴, 25°C (77°F), ...]"    ║
 ║    → 解析到 Finish → 返回最终答案                               ║
 ╚══════════════════════════════════════════════════════════════════╝
   │
   ▼
 ┌──────────────────────────────────────────────────────────────────┐
 │  Tracer.end_trace(root_span)                                     │
 │                                                                  │
 │  📊 Trace: ReActAgent.run [总耗时: 2.63s]                        │
 │  ├── 🧠 llm.call.step1 [1.23s] gpt-4o  token:320/85             │
 │  │   └── Thought: 需要查天气                                     │
 │  ├── 🔧 tool.call.Search [0.45s] "北京今日天气"                  │
 │  │   └── Observation: 北京晴, 25°C...                            │
 │  ├── 🧠 llm.call.step2 [0.89s] gpt-4o  token:450/98             │
 │  │   └── Thought: 需要转换温度                                   │
 │  ├── 🔧 tool.call.Calculator [0.02s] "25 * 9/5 + 32"            │
 │  │   └── Observation: 77.0                                       │
 │  └── ✅ Finish [0.04s]                                          │
 │                                                                  │
 │  总结: total_tokens={prompt:770, completion:183, total:953}      │
 │        tool_calls=2  │  max_step=3  │  status=OK                │
 └──────────────────────────────────────────────────────────────────┘

### 5.4 配置驱动

```yaml
# .env
LLM_PROVIDER=openai
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1

# settings.yaml
agent:
  max_steps: 5
  temperature: 0.0

tools:
  mcp_servers: []

observability:
  trace_enabled: true
  trace_export: console     # console | json | none
```

---

## 6. 项目排期

> **原则**：一小时一增量 | 接口先于实现 | 测试先于代码 | 外部依赖可 Mock

### 6.0 术语约定

| 术语 | 定义 |
|------|------|
| **框架化（framework-ify）** | 不是重写！在已有原型代码基础上统一注入：`Config` 配置驱动、`KagentError` 异常体系、`custom_prompt` 模板变量、`pip install` 入口。核心 `run()` 逻辑不动。 |
| **max_steps** | 所有 Agent 统一用 `max_steps` 表示"最大执行步数"（不再使用 `max_iterations` / `max_tool_iterations`）。每执行一次 LLM 调用 + 可能的工具调用 = 1 step。 |

### 6.1 阶段映射

| 阶段 | 对应全景文档 | 目的 | 预估任务数 |
|------|-----------|------|-----------|
| A | 阶段一 | 工程骨架 + LLM 可插拔 + 工具可插拔 | 8 |
| B | 阶段一 | 5 种 Agent 范式（Simple/ReAct 为 v0.1 必做，其余可后续实现）— **原型实现**，写入最终目录 | 6 |
| C | 阶段二 | 框架化**加固**（不是重写！给已实现的类增加：Config 注入、异常体系、`custom_prompt`、pip 可安装性） | 9 |
| D | 阶段三 | MCP 外部网关 + 链路追踪 + 容错 + 监控 | 8 |
| E | 阶段三 | 记忆系统 + 上下文工程 | 5（另有 SemanticMemory 可选任务） |
| F | 阶段四 | 端到端验收（3 个实战项目骨架） | 3 |

> **B vs C 的区别**：B 阶段实现核心逻辑（`run()` 能跑、工具能调），C 阶段在不改变核心逻辑的前提下，为已实现的类统一注入：`Config` 配置驱动、`KagentError` 异常体系、`custom_prompt` 模板变量、`pip install` 入口。不是两遍代码，而是原型 + 生产化加固。

### 6.2 进度跟踪

> **状态标记**：`[ ]` 未开始 | `[~]` 进行中 | `[x]` 已完成

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| A1 | 初始化目录树 | [x] | 2026-05-07 | pyproject.toml + 目录骨架 + .env.example |
| A2 | 引入测试框架 | [x] | 2026-05-07 | tests/ 目录 + smoke tests（pytest 待安装） |
| A3 | .env 配置加载 | [x] | 2026-05-07 | Config 类 + from_env + validate |
| A4 | LLMProvider 基类 + Registry | [x] | 2026-05-07 | LLMResponse/LLMChunk + ABC + Registry |
| A5 | AgentLLM 门面 + 配置驱动 | [x] | 2026-05-07 | PROVIDER_CONFIG + invoke/stream |
| A6 | OpenAIProvider（可插拔 Provider 示例实现） | [x] | 2026-05-07 | chat + chat_stream + LLMError |
| A7 | Tool + ToolRegistry | [x] | 2026-05-07 | Tool基类 + ToolRegistry + 19 tests |
| A8 | CalculatorTool + SearchTool | [ ] | | |
| B1 | Agent 基类 + Message 系统 | [ ] | | |
| B2 | SimpleAgent | [ ] | | |
| B3 | ReActAgent | [ ] | | |
| B4 | PlanAndSolveAgent | [ ] | | |
| B5 | ReflectionAgent | [ ] | | |
| B6 | FunctionCallAgent | [ ] | | |
| C1 | 框架目录骨架 | [ ] | | |
| C2 | Config 类 + 异常体系 | [ ] | | |
| C3 | Agent 基类框架化 | [ ] | | |
| C4 | AgentLLM 框架化（多 Provider） | [ ] | | |
| C5 | ToolRegistry 框架化（双注册） | [ ] | | |
| C6 | SimpleAgent 框架化 | [ ] | | |
| C7 | ReActAgent 框架化 | [ ] | | |
| C8 | pip install 验证 | [ ] | | |
| C9 | FunctionCallAgent 框架化 | [ ] | | |
| D1 | Span + Tracer 数据模型 | [ ] | | |
| D2 | TraceExporter | [ ] | | |
| D3 | Agent 埋点集成 | [ ] | | |
| D4 | MCPTool | [ ] | | |
| D5 | MCP Server 模板 | [ ] | | |
| D6 | MCP + ToolRegistry 集成 | [ ] | | |
| D7 | 容错机制（try/except + 幂等 + 用户可见错误） | [ ] | | |
| D8 | 监控（请求级日志 + trace_id + Token 统计） | [ ] | | |
| E1 | Memory 基类 + MemoryManager | [ ] | | |
| E2 | WorkingMemory + EpisodicMemory | [ ] | | |
| E2.5 | SemanticMemory（v0.3 可选） | [ ] | | |
| E3 | MemoryTool | [ ] | | |
| E4 | ContextBuilder | [ ] | | |
| E5 | NoteTool + TerminalTool | [ ] | | |
| F1 | 旅行助手骨架 | [ ] | | |
| F2 | 深度研究骨架 | [ ] | | |
| F3 | 赛博小镇骨架 | [ ] | | |

### 6.3 详细任务

> **任务粒度说明**：本 spec 中每个任务设计为 ~1h（含测试 → 实现 → 验收），适合排期估算。在 `writing-plans` 阶段，每个任务将进一步拆分为 2-5 分钟的 bite-sized steps（写失败的测试 → 跑测试确认失败 → 写最小实现 → 跑测试通过 → commit），符合 Superpowers TDD 节奏。

### A1：初始化目录树与 pyproject.toml

| 维度 | 内容 |
|------|------|
| 目标 | 创建 `kagent/` 目录骨架、`pyproject.toml`（含依赖）、`.env.example`、所有 `__init__.py`、创建 `.venv` 虚拟环境并安装依赖 |
| 文件 | `pyproject.toml` `requirements.txt` `requirements-dev.txt` `.env.example` `.gitignore`（含 `.venv/`、`.env`、`__pycache__/`） `kagent/__init__.py` `kagent/core/__init__.py` `kagent/agents/__init__.py` `kagent/tools/__init__.py` `kagent/tools/builtin/__init__.py` `kagent/memory/__init__.py` `kagent/context/__init__.py` |
| pyproject.toml 依赖 | 按 §3.0 依赖清单完整声明，不得遗漏或自行引入未列出的库 |
| requirements.txt | 与 `pyproject.toml` 的 `[project.dependencies]` 保持一致，开源用户 `pip install -r requirements.txt` 即可 |
| requirements-dev.txt | `-r requirements.txt` + `[project.optional-dependencies].dev` 中的包 |
| .env.example | `LLM_PROVIDER=openai` `LLM_MODEL_ID=gpt-4o` `LLM_API_KEY=your-api-key-here` `LLM_BASE_URL=https://api.openai.com/v1` `LLM_TIMEOUT=60` `SEARCH_BACKEND=serpapi` `SERPAPI_API_KEY=` `TAVILY_API_KEY=` `TRACE_ENABLED=true` `TRACE_EXPORT=console` `LOG_LEVEL=INFO` `DEBUG=false` `MAX_HISTORY_LENGTH=50` `MAX_STEPS=5` |
| 验收 | `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt` 成功 `pip install -e ".[dev]"` 成功 `python -c "import kagent"` 不报错 `python -c "import kagent.memory; import kagent.context"` 不报错 `pyproject.toml` 包含全部依赖 `requirements.txt` 与 `pyproject.toml` 的 `[project.dependencies]` 一致 `pytest -q tests/unit/test_smoke.py` 通过 |
| 测试 | `python -m compileall kagent/` |


### A2：引入测试框架

| 维度 | 内容 |
|------|------|
| 目标 | 创建 `tests/` 目录、pytest 配置、冒烟测试 |
| 文件 | `pyproject.toml`（添加 pytest 配置） `tests/__init__.py` `tests/unit/__init__.py` `tests/unit/test_smoke.py` `tests/fixtures/.env.test` |
| 类/函数 | `test_import()` — 验证 `import kagent` 成功 |
| 验收 | `pytest -q` 通过冒烟测试 |
| 测试 | `pytest -q tests/unit/test_smoke.py` |


### A3：.env 配置加载

| 维度 | 内容 |
|------|------|
| 目标 | 实现 `Config` 类，从 `.env` 文件 + 环境变量读取所有配置，必填字段校验 |
| 文件 | `kagent/core/config.py`（`.env.example` 已在 A1 创建） |
| 类/函数 | `Config` (Pydantic BaseModel) — `default_provider: str = "openai"`, `default_model: str = "gpt-4o"`, `temperature: float = 0.0`, `max_tokens: int | None = None`, `debug: bool = False`, `log_level: str = "INFO"`, `max_history_length: int = 50`, `max_steps: int = 5`, `trace_enabled: bool = True`, `trace_export: str = "console"` `Config.from_env()` — 从环境变量创建（优先读 `.env` 文件 via `dotenv`） `validate_config()` — 校验 `LLM_PROVIDER` 存在、`LLM_API_KEY` 非空（ollama/vllm 除外） |
| 验收 | `Config.from_env()` 在有 `.env` 文件时返回有效 Config 实例 缺 `LLM_API_KEY` 且 Provider 非 ollama/vllm 时抛 `ConfigError` 并包含可读错误信息 `Config().debug == False` 默认值正确 `Config.from_env().model_dump()` 返回完整字典 |
| 测试 | `pytest -q tests/unit/test_config.py` |


### A4：LLMProvider 基类 + LLMProviderRegistry

| 维度 | 内容 |
|------|------|
| 目标 | 定义 LLM Provider 的抽象接口和注册中心 |
| 文件 | `kagent/core/llm.py` |
| 类/函数 | `LLMResponse(BaseModel)` / `LLMChunk(BaseModel)` `LLMProvider(ABC)` — `chat(messages, model, temperature, tools=None, tool_choice=None) -> LLMResponse` / `chat_stream(...) -> Iterator[LLMChunk]` `LLMProviderRegistry` — `register(name, provider)` / `get(name)` / `list_providers()` |
| 验收 | `LLMProvider()` 不能直接实例化 `registry.register("test", mock_provider)` 后 `registry.get("test")` 返回 mock_provider `registry.get("nonexistent")` 抛 `ValueError` |
| 测试 | `pytest -q tests/unit/test_llm.py -k "test_provider_registry"` |


### A5：AgentLLM 门面 + 配置驱动选择

| 维度 | 内容 |
|------|------|
| 目标 | 实现 `AgentLLM` 类，从配置读取 Provider 名称并自动选择 |
| 文件 | `kagent/core/llm.py` |
| 类/函数 | `PROVIDER_CONFIG` 配置字典 `AgentLLM.__init__(provider=None, model=None, api_key=None, base_url=None, timeout=60)` `AgentLLM.register_provider(name, provider)` 类方法 `AgentLLM.invoke(messages, temperature, tools=None, tool_choice=None) -> LLMResponse` 非流式 `AgentLLM.stream(messages, temperature, tools=None) -> Iterator[LLMChunk]` 流式 |
| 验收 | `AgentLLM()` 自动读取 `LLM_PROVIDER` 环境变量 `AgentLLM.register_provider("test", mock)` 后 `AgentLLM(provider="test")` 使用 mock 缺 Provider 时抛 `ConfigError` |
| 测试 | `pytest -q tests/unit/test_llm.py -k "test_agent_llm_init"` |


### A6：OpenAIProvider（可插拔 Provider 示例实现）

| 维度 | 内容 |
|------|------|
| 目标 | 实现首个具体 Provider，验证 A4/A5 的可插拔架构可用：实现 `LLMProvider` 接口 → 注册到 `LLMProviderRegistry` → 改 `.env` 一行配置即可切换。OpenAI 兼容接口作为 v0.1 MVP 的默认实现，但架构上不绑定任何特定服务商 |
| 文件 | `kagent/core/llm.py` |
| 类/函数 | `OpenAIProvider(api_key, base_url, timeout)` — 实现 `LLMProvider.chat() -> LLMResponse` + `chat_stream() -> Iterator[LLMChunk]`，内部使用 `openai` SDK 的 `chat.completions.create`。构造函数参数全部从 `PROVIDER_CONFIG` + `.env` 自动注入，用户无需手写 |
| 验收 | Mock OpenAI API 响应 → `provider.chat()` 返回 `LLMResponse(content="...")` `provider.chat_stream()` yield 多个 `LLMChunk` API 超时 → 抛 `LLMError` 验证：切换 `LLM_PROVIDER=ollama` + `LLM_BASE_URL=http://localhost:11434/v1` 后，只需实现一个新的 `OllamaProvider(LLMProvider)` 并注册，Agent 代码零改动 |
| 测试 | `pytest -q tests/unit/test_llm.py -k "test_openai_provider"` |

> **可插拔验证**：A6 的核心价值是证明"写一个类 + 一行注册 = 接入新服务商"的架构可行。OllamaProvider / ZhipuProvider 等在 C4 实现，但只需实现 `LLMProvider` 接口并注册即可，Agent 层代码零改动。


### A7：Tool 基类 + ToolRegistry

| 维度 | 内容 |
|------|------|
| 目标 | 定义 Tool 抽象接口和可插拔注册中心 |
| 文件 | `kagent/tools/base.py` `kagent/tools/registry.py` |
| 类/函数 | `ToolResult(BaseModel)` — `content`, `success`, `error`, `metadata` `ToolParameter(BaseModel)` — `name`, `type`, `description`, `required`, `default` `Tool(ABC)` — `run(parameters) -> ToolResult` / `get_parameters() -> list[ToolParameter]` / `to_openai_schema()` `ToolRegistry` — `register_tool(tool)` / `register_function(name, desc, func)` / `unregister(name)` / `execute_tool(name, arguments) -> ToolResult` / `get_tools_description() -> str` |
| 验收 | `Tool()` 不能直接实例化 `registry.register_function("echo", "...", lambda args: args["text"])` 后 `registry.execute_tool("echo", {"text": "hi"})` 返回 `ToolResult(success=True, content="hi")` `registry.unregister("echo")` 后 `registry.execute_tool("echo", ...)` 返回 `ToolResult(success=False, content="[ERROR] 工具 'echo' 未注册")` |
| 测试 | `pytest -q tests/unit/test_tools.py -k "test_registry"` |


### A8：CalculatorTool + SearchTool

| 维度 | 内容 |
|------|------|
| 目标 | 实现两个内置工具作为 Tool 子类示例 |
| 文件 | `kagent/tools/builtin/calculator.py` `kagent/tools/builtin/search.py` |
| 类/函数 | `CalculatorTool(Tool)` — `run({"expression": "2+3*4"}) -> ToolResult`，用 `ast` 安全解析 `SearchTool(Tool)` — v0.1 使用单一搜索后端（SerpApi 或 Tavily 二选一，由环境变量 `SEARCH_BACKEND` + 对应 API Key 决定），不做降级链 |
| 验收 | `calculator.run({"expression": "2+3*4"}).content` 返回 `"14"` `calculator.run({"expression": "sqrt(16)"}).content` 返回 `"4.0"` `search.run({"query": "Python"})` 返回 `ToolResult(success=True, content=非空)`（需配置 API Key）；未配置 API Key → 返回 `ToolResult(success=False, content="[ERROR] 搜索 API Key 未配置")` |
| 测试 | `pytest -q tests/unit/test_tools.py -k "test_calculator"` |


### B1：Agent 基类 + Message 系统

| 维度 | 内容 |
|------|------|
| 目标 | 定义所有 Agent 的统一接口和消息格式 |
| 文件 | `kagent/core/agent.py` `kagent/core/message.py` |
| 类/函数 | `Message(BaseModel)` — `content`, `role: Literal["user","assistant","system","tool"]`, `timestamp`, `metadata`, `to_dict()` `Agent(ABC)` — `__init__(name, llm, system_prompt, config)` / `@abstractmethod run(input_text) -> str` / `add_message()` / `clear_history()` / `get_history()` |
| 验收 | `Agent()` 不能直接实例化 `Message(...)` 创建后 `to_dict()` 返回 OpenAI 格式 `{"role": ..., "content": ...}` |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_message"` |


### B2：SimpleAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现基础对话 Agent，支持可选工具调用 |
| 文件 | `kagent/agents/simple_agent.py` |
| 类/函数 | `SimpleAgent(Agent)` — `run(input_text, max_steps=3)` `_run_with_tools(messages, input_text, max_steps)` — 循环 LLM + 工具 `_parse_tool_calls(text) -> list` — 正则匹配 `[TOOL_CALL:name:params]` `_execute_tool_call(tool_name, parameters) -> ToolResult` `add_tool(tool)` / `remove_tool(tool_name)` / `stream_run(input_text)` |
| 验收 | 无工具时直接返回 LLM 响应 有工具时能解析 `[TOOL_CALL:calc:1+1]` 并执行 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_simple_agent"` |


### B3：ReActAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Thought→Action→Observation 循环 |
| 文件 | `kagent/agents/react_agent.py` |
| 类/函数 | `ReActAgent(Agent)` — `run(input_text, max_steps=5)` `_parse_output(text) -> (thought, action)` — 正则匹配 `Thought:...\nAction:...` `_parse_action(action_text) -> (tool_name, tool_input)` |
| Action 格式 | **`Action: ToolName[parameters]`** — 调用工具（parameters 为字符串，直接传给 `execute_tool(name, {"query": parameters})`）。**`Action: Finish[最终答案]`** — 终止循环，返回 `[最终答案]`。示例：`Action: Search[北京天气]` / `Action: Calculator[25 * 9/5 + 32]` / `Action: Finish[北京今天晴，25°C]` |
| 验收 | Mock LLM 返回 `Action: Finish[答案]` → `run()` 返回答案 Mock LLM 返回 `Action: Search[query]` → 调用 SearchTool → 继续循环 达到 max_steps 后终止 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_react_agent"` |


### B4：PlanAndSolveAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Plan → Execute 两阶段 Agent |
| 文件 | `kagent/agents/plan_solve_agent.py` |
| 类/函数 | `PlanAndSolveAgent(Agent)` — `run(input_text)` `_plan(question) -> list[str]` — LLM 生成 Python 列表，`ast.literal_eval` 解析 `_execute(question, plan) -> str` — 逐步执行，每步带完整上下文 |
| 验收 | Mock LLM 返回 `["步骤1", "步骤2"]` → 依次执行 → 返回最后结果 解析失败时抛 AgentError |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_plan_solve"` |


### B5：ReflectionAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Execute→Reflect→Refine 迭代 Agent |
| 文件 | `kagent/agents/reflection_agent.py` |
| 类/函数 | `ReflectionAgent(Agent)` — `run(input_text, max_steps=3)` 三阶段 Prompt：`initial` / `reflect` / `refine` |
| 验收 | Mock LLM reflect 返回 `无需改进` → 终止循环 达到 max_steps → 返回最后一版 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_reflection"` |


### B6：FunctionCallAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现基于 OpenAI 原生 Function Calling 的 Agent（替代 Prompt 约束方式） |
| 文件 | `kagent/agents/function_call_agent.py` |
| 类/函数 | `FunctionCallAgent(Agent)` — `run(input_text)` `_build_tool_schemas() -> list[dict]` — 从 ToolRegistry 生成 OpenAI tools 格式 `_invoke_with_tools(messages, tools, tool_choice) -> LLMResponse` — 通过 `AgentLLM.invoke(..., tools=...)` 调用支持工具协议的 Provider `_extract_message_content(response) -> str` — 提取文本内容 `_parse_function_call_arguments(function_call) -> dict` — 解析 JSON 参数 |
| 验收 | Mock OpenAI 返回 `tool_calls` → Agent 执行工具 → 结果注入 messages → 二次调用 `tool_choice="auto"` 时 LLM 自主决定是否调用工具 工具执行超时 → 返回 timeout 错误信息，不中断循环 调用不存在的工具 → 返回 "Tool not found" 错误，LLM 可选择其他工具 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_function_call"` |


### C1：框架目录骨架（验证 + 补充）

| 维度 | 内容 |
|------|------|
| 目标 | 验证 A1 创建的目录树与 5.2 节一致，补充遗漏的 `__init__.py`，确保 `python -m compileall kagent/` 通过 |
| 文件 | 检查并补充 `kagent/` 下所有 `__init__.py`（A1 已创建主要目录，C1 只做验证+修补） |
| 类/函数 | 无 |
| 验收 | `python -m compileall kagent/` 通过；`pip install -e .` 后 `from kagent import SimpleAgent, ReActAgent, AgentLLM, Config` 全部可用 |
| 测试 | `python -c "from kagent import SimpleAgent, ReActAgent, AgentLLM, Config; print('OK')"` |


### C2：Config 类 + 异常体系

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Pydantic Config + 结构化异常 |
| 文件 | `kagent/core/config.py` `kagent/core/exceptions.py` |
| 类/函数 | `Config(BaseModel)` — 所有配置项 + `from_env()` `KagentError(Exception)`, `AgentError`, `LLMError`, `ToolError`, `ConfigError` |
| 验收 | `Config.from_env()` 自动读取环境变量 `LLMError("msg")` / `AgentError("msg")` 继承自 `KagentError` |
| 测试 | `pytest -q tests/unit/test_config.py` |


### C3：Agent 基类框架化（注入 Config + custom_prompt）

| 维度 | 内容 |
|------|------|
| 目标 | B1 的 Agent 基类已在 `kagent/core/agent.py`，本任务不移动文件——只给已有 Agent 基类注入：`Config` 参数、`custom_prompt` 模板变量、`run_id` 属性 |
| 文件 | `kagent/core/agent.py`（修改） |
| 类/函数 | `Agent.__init__` 增加 `config: Config | None = None` + `custom_prompt: str | None = None`；新增 `run_id` 属性（`uuid.uuid4().hex[:8]`），每次 `run()` 调用生成新 ID |
| 验收 | `agent = SimpleAgent(name="test", llm=mock_llm, config=Config.from_env(), custom_prompt="{tools}\n{input}")` 创建成功 `agent.run_id` 每次调用不同 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_agent_config or test_custom_prompt"` |


### C4：AgentLLM 框架化（多 Provider + 自动检测）

| 维度 | 内容 |
|------|------|
| 目标 | 升级 AgentLLM，增加 Ollama/VLLM/Zhipu Provider + `auto` 自动检测 |
| 文件 | `kagent/core/llm.py` |
| 类/函数 | 新增 `OllamaProvider`, `VLLMProvider`, `ZhipuProvider` `AgentLLM._auto_detect()` — 环境变量 → URL 解析 → API Key 格式 `PROVIDER_CONFIG` 字典扩充 |
| 验收 | `LLM_PROVIDER=auto` + `LLM_BASE_URL=http://localhost:11434/v1` → 自动选择 ollama `LLM_PROVIDER=auto` + `OPENAI_API_KEY=sk-xxx` → 选择 openai |
| 测试 | `pytest -q tests/unit/test_llm.py -k "test_auto_detect"` |


### C5：ToolRegistry 框架化（双注册 + 拔除）

| 维度 | 内容 |
|------|------|
| 目标 | 升级 ToolRegistry 支持 Tool 对象 + 裸函数双重注册 |
| 文件 | `kagent/tools/registry.py` |
| 类/函数 | `ToolRegistry._tools: dict` + `ToolRegistry._functions: dict` `register_tool(tool: Tool)` / `register_function(name, desc, func)` `get_tools_description()` — 合并两种来源 |
| 验收 | 同时注册 Tool 对象和裸函数 → `get_tools_description()` 包含两者 `unregister` 后 description 不包含该工具 |
| 测试 | `pytest -q tests/unit/test_tools.py -k "test_registry_framework"` |


### C6：SimpleAgent 框架化

| 维度 | 内容 |
|------|------|
| 目标 | 将 B2 的 SimpleAgent 迁移到框架目录 |
| 文件 | `kagent/agents/simple_agent.py` |
| 类/函数 | `SimpleAgent` — 从手写版迁移，增加 Config 支持、异常处理、`stream_run()` |
| 验收 | 与 B2 功能一致 + `agent.config` 可用 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_simple_agent"` |


### C7：ReActAgent 框架化

| 维度 | 内容 |
|------|------|
| 目标 | 将 B3 的 ReActAgent 迁移到框架目录 |
| 文件 | `kagent/agents/react_agent.py` |
| 类/函数 | `ReActAgent` — 使用统一 ToolRegistry、支持 `custom_prompt`（模板变量见 Agent 基类 `__init__` 文档）、使用 Message 系统 |
| 验收 | 与 B3 功能一致 + `custom_prompt="{custom_field}"` → 生成 Prompt 中实际包含 `custom_field` 内容 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_react_agent"` |


### C8：pip install 验证

| 维度 | 内容 |
|------|------|
| 目标 | 创建 `pyproject.toml` 完成，`pip install -e .` 可安装 |
| 文件 | `pyproject.toml` `README.md`（最少内容） |
| 类/函数 | 无 |
| 验收 | `pip install -e .` 成功 `python -c "from kagent import SimpleAgent, AgentLLM; print('OK')"` 输出 OK |
| 测试 | 手动执行验证命令 |


### C9：FunctionCallAgent 框架化

| 维度 | 内容 |
|------|------|
| 目标 | 将 B6 的 FunctionCallAgent 迁移到框架目录，增加并行工具调用支持 |
| 文件 | `kagent/agents/function_call_agent.py` |
| 类/函数 | `FunctionCallAgent` — 使用统一 ToolRegistry、`to_openai_schema()`、并行工具调用 |
| 验收 | 与 B6 功能一致 + 支持并行工具调用（多个 tool_calls 同时执行） `tool_choice` 参数可配置 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "test_function_call"` |


### D1：Span + Tracer 数据模型

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Span 数据类和 Tracer 单例 |
| 文件 | `kagent/core/tracing.py` |
| 类/函数 | `SpanStatus(str, Enum)` — OK / ERROR `SpanType(str, Enum)` — AGENT_RUN / AGENT_STEP / LLM_CALL / TOOL_CALL `Span` (dataclass) — 所有字段见 3.4 `Tracer` (单例) — `start_trace()` / `start_span()` / `end_span()` / `span()` context manager / `add_event()` / `get_current_trace()` / `get_all_traces()` / `clear()` |
| 验收 | `start_trace → start_span → end_span → end_span` 生成正确 parent/children 树 context manager 自动处理异常 duration_ms 自动计算 |
| 测试 | `pytest -q tests/unit/test_tracing.py -k "test_tracer"` |


### D2：TraceExporter

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Trace 树的导出（dict / JSON / 终端树形图） |
| 文件 | `kagent/core/tracing.py` |
| 类/函数 | `TraceExporter.to_dict(span) -> dict` — 递归 `TraceExporter.to_json(span, indent) -> str` `TraceExporter.to_tree(span, indent) -> str` — 彩色树形输出 |
| 验收 | `to_dict` 包含所有字段且 children 递归 `to_json` 可解析回 dict `to_tree` 输出包含 span name + duration_ms |
| 测试 | `pytest -q tests/unit/test_tracing.py -k "test_exporter"` |


### D3：Agent 埋点集成

| 维度 | 内容 |
|------|------|
| 目标 | 将 Tracer 埋入 ReActAgent + SimpleAgent |
| 文件 | `kagent/agents/react_agent.py` `kagent/agents/simple_agent.py` |
| 类/函数 | `ReActAgent.__init__` 增加 `enable_tracing: bool = True` `ReActAgent.run()` 中埋入 trace/step/llm/tool spans `SimpleAgent.run()` 中埋入基础 traces |
| 验收 | 跑一次 Agent → `Tracer().get_current_trace()` 返回非空 Span 树 树包含 AGENT_RUN → AGENT_STEP → LLM_CALL 层次 工具调用时有 TOOL_CALL Span |
| 测试 | `pytest -q tests/integration/test_agent_with_tracing.py` |


### D4：MCPTool

| 维度 | 内容 |
|------|------|
| 目标 | 实现 MCP 协议客户端，将一个 MCP Server 的工具映射为本地 Tool |
| 文件 | `kagent/tools/mcp_tool.py` |
| 类/函数 | `MCPTool.__init__(server_command: list[str])` — 启动子进程、建立通信 `MCPTool.discover_tools() -> list[Tool]` — 调用 `tools/list` `MCPTool.call_tool(name, arguments) -> ToolResult` — 调用 `tools/call` `MCPTool.close()` — 清理子进程 |
| 验收 | 启动一个 MCP Server → `discover_tools()` 返回非空列表 `call_tool("tool_name", {})` 返回正确结果 子进程异常时抛 `ToolError` |
| 测试 | `pytest -q tests/integration/test_mcp.py` |


### D5：MCP Server 模板

| 维度 | 内容 |
|------|------|
| 目标 | 提供一个可复用的 MCP Server 模板（用于 RAG 项目接入） |
| 文件 | `kagent/tools/mcp_server_template.py`（示例文件） |
| 类/函数 | `mcp_server_example` — 暴露 `search_docs` + `list_sources` 两个 Tool |
| 验收 | 运行该 Server → D4 的 MCPTool 能连接并发现工具 |
| 测试 | `pytest -q tests/integration/test_mcp.py -k "test_mcp_connect_and_discover"` — 使用 subprocess 在测试中启动/销毁 MCP Server，不依赖手动操作 |


### D6：MCP + ToolRegistry 集成

| 维度 | 内容 |
|------|------|
| 目标 | ToolRegistry 支持 `register_mcp()` 方法 |
| 文件 | `kagent/tools/registry.py` |
| 类/函数 | `ToolRegistry.register_mcp(mcp_tool)` — 自动发现 + 批量注册 `ToolRegistry.unregister(name)` — 拔除单个工具 |
| 验收 | 注册 MCPTool → `get_tools_description()` 包含 MCP 工具 拔除 → description 不再包含 |
| 测试 | `pytest -q tests/integration/test_mcp.py` |


### D7：容错机制（try/except + 幂等 + 用户可见错误）

| 维度 | 内容 |
|------|------|
| 目标 | 为框架所有关键路径建立统一的错误处理、幂等保护和用户可见错误信息 |
| 文件 | `kagent/tools/registry.py` `kagent/tools/mcp_tool.py` `kagent/agents/react_agent.py` `kagent/agents/function_call_agent.py` |
| 类/函数 | `ToolRegistry.execute_tool()` — try/except 包裹，工具执行异常返回 `ToolResult(success=False, content="[ERROR] 工具 '{name}' 执行失败: {message}")` 而非抛异常 `MCPTool.call_tool()` — 子进程断开时自动重连（最多 3 次），超时 30s 后返回用户可读错误 `ReActAgent.run()` — 解析失败时在 history 中注入 `"Observation: 格式错误，请严格遵循 Thought/Action 格式，重新尝试"` `FunctionCallAgent._invoke_with_tools()` — API 超时/限流时指数退避重试（1s→2s→4s），最多 3 次 幂等保证：`SearchTool.run()` 同一 query + 同一时间窗口（5s）返回缓存结果 所有 `KagentError` 子类携带 `user_message` 属性（给用户看）和 `debug_message`（给开发者看） |
| 验收 | 工具执行抛出 `ValueError` → Agent 收到 `ToolResult(success=False)`，不中断循环 MCP Server 进程被 kill → MCPTool 自动重连，Agent 无感知 LLM API 返回 429 → 自动退避重试，3 次均失败后抛 `LLMError` 含 user_message 同一查询 5s 内重复搜索 → 返回缓存，不发起 HTTP 请求 |
| 测试 | `pytest -q tests/unit/test_fault_tolerance.py` |


### D8：监控（请求级日志 + trace_id + Token 用量统计）

| 维度 | 内容 |
|------|------|
| 目标 | 为每次 Agent 运行建立结构化日志（含 trace_id）、统计 Token 消耗 |
| 文件 | `kagent/core/tracing.py` `kagent/core/llm.py` `kagent/core/agent.py` |
| 类/函数 | `Span.metadata` 新增 `token_usage` 字段 — `{"prompt": int, "completion": int, "total": int}` `AgentLLM.invoke()` / `AgentLLM.stream()` — 从 Provider response 提取 token usage → 自动写入当前 Span `Tracer.add_event()` 增强 — 记录关键事件：`"llm.start"` / `"llm.end"` / `"tool.start"` / `"tool.end"` / `"error"` / `"retry"` `TraceExporter.to_json()` 增加汇总统计 — `"total_tokens": {"prompt": ..., "completion": ...}` / `"total_duration_ms": ...` / `"tool_call_count": ...` `Agent` 基类增加 `run_id` 属性 — `uuid.uuid4().hex[:8]`，每次 `run()` 调用生成新 ID，注入 Tracer |
| 验收 | 跑一次 Agent → `TraceExporter.to_json(trace)` 顶层包含 `total_tokens` 汇总 `llm.call` Span 的 metadata 包含 `token_usage: {prompt: N, completion: N, total: N}` 终端树形图每行末尾显示耗时 + Token 数 `run_id` 贯穿所有 Span，日志中可 grep 定位 |
| 测试 | `pytest -q tests/unit/test_tracing.py -k "test_token_stats"` |


### E1：Memory 基类 + MemoryManager

| 维度 | 内容 |
|------|------|
| 目标 | 定义记忆系统统一接口和多后端管理器 |
| 文件 | `kagent/memory/base.py` `kagent/memory/manager.py` |
| 类/函数 | `BaseMemory(ABC)` — `store(item)` / `search(query, top_k=5)` / `clear()` `MemoryItem(BaseModel)` — `content`, `metadata`, `created_at`, `score` `MemoryManager` — 注册多个 memory backend，统一写入与检索 |
| 验收 | `BaseMemory()` 不能直接实例化 `MemoryManager` 能同时注册 Working/Episodic 后端并合并检索结果 |
| 测试 | `pytest -q tests/unit/test_memory.py -k "test_base_memory or test_memory_manager"` |


### E2：WorkingMemory + EpisodicMemory

| 维度 | 内容 |
|------|------|
| 目标 | 实现两种记忆后端 |
| 文件 | `kagent/memory/working.py` `kagent/memory/episodic.py` |
| 类/函数 | `WorkingMemory(BaseMemory)` — TTL 管理、容量限制、当前对话上下文 `EpisodicMemory(BaseMemory)` — 时间序列存储、按时间范围检索 |
| 验收 | `WorkingMemory` 超过容量自动淘汰旧记录 `EpisodicMemory` 按时间检索返回正确事件 |
| 测试 | `pytest -q tests/unit/test_memory.py` |


### E2.5：SemanticMemory（v0.3 可选）

| 维度 | 内容 |
|------|------|
| 目标 | 提供语义检索记忆后端，但不阻塞 v0.1 MVP |
| 文件 | `kagent/memory/semantic.py` |
| 类/函数 | `SemanticMemory(BaseMemory)` — 依赖可插拔 embedding 函数和向量存储适配器，默认提供内存向量索引用于测试 |
| 验收 | 存入多条文本后，语义相近 query 能返回相关记忆；无 embedding 配置时给出用户可读配置提示 |
| 测试 | `pytest -q tests/unit/test_memory.py -k "test_semantic_memory"` |


### E3：MemoryTool

| 维度 | 内容 |
|------|------|
| 目标 | 将 MemoryManager 封装为 Tool，注册到 ToolRegistry |
| 文件 | `kagent/memory/tool.py` |
| 类/函数 | `MemoryTool(Tool)` — `run({"action": "recall", "query": "..."})` / `run({"action": "remember", "content": "..."})` |
| 验收 | Agent 对话中能通过 `[TOOL_CALL:memory:action=recall,query=...]` 检索记忆 记忆在对话期间持久 |
| 测试 | `pytest -q tests/integration/test_memory_tool.py` |


### E4：ContextBuilder (GSSC)

| 维度 | 内容 |
|------|------|
| 目标 | 实现 GSSC 上下文构建流水线 |
| 文件 | `kagent/context/builder.py` |
| 类/函数 | `ContextBuilder` — `gather()` / `select(relevance_score)` / `structure(template)` / `compress(max_tokens)` / `build(**inputs) -> str` |
| 验收 | 输入 messages + tool_results → `build()` 返回不超过 max_tokens 的格式化上下文 `compress` 后 token 数 ≤ max_tokens |
| 测试 | `pytest -q tests/unit/test_context.py` |


### E5：NoteTool + TerminalTool

| 维度 | 内容 |
|------|------|
| 目标 | 提供笔记和文件系统工具 |
| 文件 | `kagent/tools/note_tool.py` `kagent/tools/terminal_tool.py` |
| 类/函数 | `NoteTool(Tool)` — 结构化笔记 CRUD `TerminalTool(Tool)` — 受限文件系统操作（read/list） |
| 验收 | `NoteTool` 能存/取笔记 `TerminalTool` 能列出指定目录文件 |
| 测试 | `pytest -q tests/unit/test_note_terminal.py` |


### F1：旅行助手骨架

| 维度 | 内容 |
|------|------|
| 目标 | 搭建旅行助手项目的最小可运行骨架 |
| 文件 | `projects/trip_planner/` 目录 `projects/trip_planner/main.py` — FastAPI 入口 + Agent 初始化 |
| 类/函数 | `TripPlannerAgent` — 继承 `SimpleAgent`，集成高德地图 MCP |
| 验收 | `python main.py` 启动后 `/api/trip/plan` 返回 200 |
| 测试 | 手动 curl 测试 |


### F2：深度研究骨架

| 维度 | 内容 |
|------|------|
| 目标 | 搭建深度研究 Agent 的最小可运行骨架 |
| 文件 | `projects/deep_research/` 目录 `projects/deep_research/main.py` |
| 类/函数 | `ResearchAgent` — PlanAndSolveAgent + SearchTool + NoteTool |
| 验收 | 传入研究主题 → 输出结构化报告（控制台） |
| 测试 | `python main.py "AI Agent 发展趋势"` |


### F3：赛博小镇骨架

| 维度 | 内容 |
|------|------|
| 目标 | 搭建赛博小镇的最小可运行骨架（Agent 后端） |
| 文件 | `projects/ai_town/` 目录 `projects/ai_town/main.py` — FastAPI + NPC Agent |
| 类/函数 | `NPCAgent` — `SimpleAgent` + MemoryTool + 角色 Prompt |
| 验收 | `/chat` API 接收消息 → NPC 基于角色设定回复 |
| 测试 | 手动 curl 测试 |


## 7. Axioms（内嵌原则）

1. **Spec before implementation** — 接口 + 契约 + 验收标准先于代码定义
2. **One hour, one verifiable increment** — 每个任务 ~1h，有可测试的输出
3. **Test-first, always** — 先写测试方法，再写代码
4. **Interfaces before implementations** — 抽象基类 + 工厂先于具体实现
5. **Configuration drives behavior** — 单一配置源，切换零代码改动
6. **Fail fast, degrade gracefully** — 启动时校验，运行时降级；工具失败返回用户可读错误，不中断 Agent 循环
7. **Observability is not optional** — 每次 run() 生成 trace_id + 结构日志 + Token 用量统计
8. **SPEC is a living document** — 每完成一个任务更新进度表
