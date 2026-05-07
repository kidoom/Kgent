## 3. 技术选型

### 3.0 依赖清单（Dependency Manifest）

> `pyproject.toml` 的 `[project.dependencies]` 和 `[project.optional-dependencies]` 必须按此表声明，不得遗漏或自行引入未列出的库。

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
