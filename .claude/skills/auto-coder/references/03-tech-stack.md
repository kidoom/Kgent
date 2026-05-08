## 3. 技术选型

### 3.0 依赖清单（Dependency Manifest）

> `pyproject.toml` 的 `[project.dependencies]` 和 `[project.optional-dependencies]` 必须按此表声明，不得遗漏或自行引入未列出的库。用户通过 `pip install -e ".[dev]"` 即可搭建开发环境。

#### v0.1 核心依赖（`pip install kagent`）

| 包名 | 版本约束 | 用途 | 引入阶段 |
|------|---------|------|---------|
| `openai` | `>=1.0` | OpenAI 兼容 LLM 调用（`chat.completions.create`），自带 `httpx` 作为 transitive 依赖 | A6 |
| `pydantic` | `>=2.0` | 数据模型校验（`BaseModel`, `Field`, `ValidationError`） | A3 |
| `python-dotenv` | `>=1.0` | `.env` 文件加载到 `os.environ` | A3 |
| `tavily-python` | `>=0.3` | SearchTool 默认 `tavily` 后端客户端；真实调用测试需 `TAVILY_API_KEY` 且标记 `external` | A8 |

> 不在 v0.1 直接依赖里：`httpx`（OpenAI SDK 已 transitive 引入；如需自建 HTTP 客户端再显式加）；`pyyaml`（settings.yaml 推迟到 v0.3+）；`requests`（SerpApi 备用后端用标准库 `urllib.request`）。

#### v0.2+ 可选依赖（`pip install kagent[mcp]` / `kagent[memory]` / `kagent[examples]`）

| 包名 | 版本约束 | 用途 | 引入阶段 | extra name |
|------|---------|------|---------|-----------|
| `mcp` | `>=1.0` | MCP 协议客户端（`MCPTool` 连接外部 MCP Server） | D | `mcp` |
| `pyyaml` | `>=6.0` | settings.yaml 解析（v0.3+ 引入分层配置后启用） | D | `mcp` 或独立 `config` |
| `numpy` | `>=1.24` | SemanticMemory 向量检索（余弦相似度计算） | E | `memory` |
| `fastapi` | `>=0.100` | 实战示例的 HTTP API 入口 | F | `examples` |
| `uvicorn` | `>=0.20` | ASGI 服务器（配合 FastAPI） | F | `examples` |

#### 开发依赖（`pip install kagent[dev]`）

| 包名 | 版本约束 | 用途 | 何时加入 |
|------|---------|------|---------|
| `pytest` | `>=7.0` | 单元/集成测试框架 | A2 |
| `pytest-cov` | `>=4.0` | 覆盖率报告 | A2 |
| `pytest-asyncio` | `>=0.21` | async 测试支持（**当首次出现 async 接口时再加**，v0.1 暂不需要） | v0.2+ |

#### 标准库（无需声明，仅作记录）

| 模块 | 用途 | 引入阶段 |
|------|------|---------|
| `ast` | CalculatorTool 安全表达式解析 | A8 |
| `math`, `operator` | CalculatorTool 数学函数 + 操作符表 | A8 |
| `urllib.request`, `urllib.parse`, `json` | SearchTool（SerpApi 备用后端）HTTP 调用 | A8 |
| `re` | Agent 输出正则解析（Thought/Action 提取） | B |
| `uuid` | `run_id` 生成、`trace_id` / `span_id` 生成 | C / D |
| `dataclasses` | `Span` 数据类定义（`@dataclass` + `field`） | D |
| `contextvars` | `Tracer` 并发隔离（`ContextVar`） | D |
| `time` | `start_time` / `end_time` 记录 | D |
| `subprocess` | MCP Server 子进程启动/管理 | D |
| `sqlite3` | EpisodicMemory 持久化 | E |
| `collections` | `OrderedDict`（WorkingMemory 容量淘汰） | E |
| `typing` | 类型注解（`Literal`, `Iterator`, `Any`） | 全阶段 |
| `importlib` | A5 PROVIDER_CONFIG.class 反射 lazy-load | A5 |
| `threading` | ToolRegistry 注册/注销加锁（v0.3+ 多线程场景，D7） | D |


#### pyproject.toml 完整声明（v0.1）

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"     # ⚠️ 标准 backend，不要写 setuptools.backends._legacy:_Backend

[project]
name = "kagent"
version = "0.1.0"
description = "Pluggable AI Agent Framework"
requires-python = ">=3.10"
dependencies = [
    "openai>=1.0",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "tavily-python>=0.3",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]
# v0.2+ 启用：
# mcp = ["mcp>=1.0", "pyyaml>=6.0"]
# memory = ["numpy>=1.24"]
# examples = ["fastapi>=0.100", "uvicorn>=0.20"]

[tool.setuptools.packages.find]
include = ["kagent*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
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

**配置（v0.1 单一配置源 — 所有 Provider 共用同一组 env）：**
```yaml
# .env
LLM_PROVIDER=openai          # v0.1: openai | ollama | vllm  ｜ v0.2+: + modelscope | zhipu | auto
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=sk-xxx           # ollama / vllm 可空
LLM_BASE_URL=                # 可选，留空时走 PROVIDER_CONFIG[name].default_base_url
LLM_TIMEOUT=60               # HTTP 超时（秒）
```

> **设计原则**：`LLM_API_KEY` / `LLM_BASE_URL` 是单一来源，**不再为每个 Provider 设独立 env**（如 `OPENAI_API_KEY`、`MODELSCOPE_API_KEY` 等），切 Provider 只需改 `LLM_PROVIDER` 一行。这是"切换零代码改动"承诺的代码体现。

**工厂模式（内嵌在 AgentLLM 构造函数中）：**
```python
class AgentLLM:
    _registry = LLMProviderRegistry()

    @classmethod
    def register_provider(cls, name: str, provider: LLMProvider): ...

    def __init__(self, provider=None, model=None, api_key=None,
                 base_url=None, timeout=60, config=None):
        # 1. 读取 Config（默认从 .env） → 解析最终 provider/model/api_key/base_url/timeout
        # 2. _get_or_load_provider(): 先查 _registry；
        #    未注册则查 PROVIDER_CONFIG[name].class → importlib 反射 → 用解析出来的
        #    api_key/base_url/timeout 实例化 → register 进 _registry
        # 3. 仍失败抛 ConfigError（含已注册 + 已知 PROVIDER_CONFIG 列表）
        ...

    def invoke(self, messages: list[dict], temperature=None,
               tools: list[dict] | None = None,
               tool_choice: str | dict | None = None, **kwargs) -> LLMResponse: ...
    def stream(self, messages: list[dict], temperature=None,
               tools: list[dict] | None = None, **kwargs): ...  # Iterator[LLMChunk]
```

**Provider 配置字典（`PROVIDER_CONFIG`）—— v0.1 必须包含 `class` 字段以支持 lazy-load：**

```python
PROVIDER_CONFIG: dict[str, dict] = {
    # v0.1 内置
    "openai": {
        "class": "kagent.core.llm.providers.OpenAIProvider",
        "default_base_url": "https://api.openai.com/v1",
        "requires_api_key": True,
    },
    "ollama": {
        "class": "kagent.core.llm.providers.OpenAIProvider",  # 复用 OpenAI 兼容接口
        "default_base_url": "http://localhost:11434/v1",
        "requires_api_key": False,
    },
    "vllm": {
        "class": "kagent.core.llm.providers.OpenAIProvider",  # 同上
        "default_base_url": "http://localhost:8000/v1",
        "requires_api_key": False,
    },
    # v0.2+ (C4 阶段添加，需要专门的 Provider 子类)
    # "modelscope": {"class": "kagent.core.llm.providers.ModelScopeProvider", ...},
    # "zhipu":      {"class": "kagent.core.llm.providers.ZhipuProvider", ...},
}
```

**`_get_or_load_provider` 算法：**
```
1. if name in self._registry:                           # 已显式注册过的 mock/test 实例优先
       return registry[name]
2. if name not in PROVIDER_CONFIG:
       raise ConfigError(f"未知 provider '{name}'，可用: {list(PROVIDER_CONFIG)}")
3. cfg = PROVIDER_CONFIG[name]
4. if cfg["requires_api_key"] and not self.api_key:
       raise ConfigError(f"provider '{name}' 需要 LLM_API_KEY")
5. base_url = self.base_url or cfg["default_base_url"]
6. cls = importlib.import_module(...).getattr(class_name)   # 反射 import
7. provider = cls(api_key=self.api_key, base_url=base_url, timeout=self.timeout)
8. self._registry.register(name, provider)              # 缓存
9. return provider
```

**降级策略**：Provider 不可用时抛出 `LLMError`，Agent 层捕获后（v0.3 起，D 阶段引入 Tracer）记录 Trace 并终止。v0.1/v0.2 直接向上抛。

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

**配置（v0.3+ 预留；v0.1 仅使用 `.env`，见 §5.4）：**
```yaml
# settings.yaml（v0.3+）
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

> 工具系统的具体降级与重试策略统一汇总在 §3.7 运行时契约。本节只定义接口契约，不重复策略文字。

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
    """v0.1 双字段异常基类。

    A 阶段（A3 之前已有）允许单字段简化版：KagentError(message)。
    C2 任务负责升级为双字段并迁移所有 raise：
      - user_message: 给最终用户看的消息（脱敏，可写入 LLM 上下文）
      - debug_message: 给开发者看的（含路径、HTTP 原文、stack 摘要等）
    Trace / 日志默认只导出 user_message；debug_message 仅在 Config.debug=True 时导出。
    """
    def __init__(self, user_message: str, debug_message: str | None = None):
        self.user_message = user_message
        self.debug_message = debug_message
        super().__init__(user_message)

class AgentError(KagentError): ...
class LLMError(KagentError): ...
class ToolError(KagentError): ...
class ConfigError(KagentError): ...
```

> **A→C 迁移路径**：A 阶段已有的 `LLMError(str(e))` / `ConfigError(msg)` 等单参调用在 C2 升级时**保持向后兼容**：把 `__init__` 写成 `def __init__(self, user_message, debug_message=None)`，老代码 `LLMError("foo")` 自动落入 `user_message="foo", debug_message=None`，无需改 raise 处。新代码可用 `LLMError("API 暂不可用，请稍后重试", debug_message=f"HTTP 503 from {url}: {raw}")`。

### 3.7 运行时契约（单一来源 — 所有阶段共同遵守）

> 此节是所有"降级 / 重试 / 幂等 / 并发 / 安全"约束的**唯一权威来源**。其他章节只引用本节、不重复策略文字。
> 表格的"v0.x 起"列说明该约束在哪个版本开始生效；之前可以放宽。

#### 3.7.1 工具执行（`ToolRegistry.execute_tool`）

| # | 约束 | v0.x 起 | 实现位置 |
|---|------|---------|---------|
| T1 | 工具未注册 → 返回 `ToolResult(success=False, content="[ERROR] 工具 '{name}' 未注册", error="tool_not_found")`，**不抛** | v0.1 | `registry.py` |
| T2 | 工具被 `disable()` → 返回 `ToolResult(success=False, content="[ERROR] 工具 '{name}' 已被禁用", error="tool_disabled")` | v0.1 | `registry.py` |
| T3 | 工具 `run()` 抛异常 → 捕获并返回 `ToolResult(success=False, content="[ERROR] 工具 '{name}' 执行失败: {e}", error=str(e))`，**绝不向上抛** | v0.1 | `registry.py` |
| T4 | 工具结果统一带 `metadata`，敏感字段（api_key/cookie/...）必须在工具内部脱敏后再放入 `metadata` | v0.1 | 各 Tool 实现 |
| T5 | `register_tool` / `unregister` / `disable` / `enable` 必须线程安全（加 `threading.Lock`）；`execute_tool` 取 dict 不可变快照 | **v0.3 起 (D7)**（v0.1/v0.2 单线程默认） | `registry.py` |

#### 3.7.2 LLM 调用（`AgentLLM.invoke` / `OpenAIProvider.chat`）

| # | 约束 | v0.x 起 | 实现位置 |
|---|------|---------|---------|
| L1 | Provider 不可用（PROVIDER_CONFIG 无该项 / 反射 import 失败 / 缺 API Key）→ 启动期抛 `ConfigError`（fail-fast） | v0.1 | `factory.py` |
| L2 | OpenAI SDK 抛任意异常 → 包装为 `LLMError(user_message="LLM 调用失败", debug_message=str(e))` 向上抛 | v0.1 | `providers.py` |
| L3 | API 超时 / 429 限流 → 指数退避重试（1s → 2s → 4s，最多 3 次），3 次均失败抛 `LLMError` | **v0.3 起 (D7)**（v0.1/v0.2 直接抛） | `providers.py` 或 `factory.py` |
| L4 | OpenAI client 在 `Provider.__init__` 创建一次并复用（连接池）；不要每次 `chat()` 都 new | v0.1 | `providers.py` |
| L5 | `LLMResponse.raw` 默认不进入日志/导出；`Config.debug=True` 时才允许导出 | v0.1 | `providers.py` + 后续 Tracer |

#### 3.7.3 Agent 循环（`Agent.run`）

| # | 约束 | v0.x 起 | 实现位置 |
|---|------|---------|---------|
| A1 | `max_steps` 是硬上限，超过后强制返回当前状态最佳结果（不抛异常） | v0.1 | `simple_agent.py` / `react_agent.py` |
| A2 | LLM 输出格式不合法（ReAct 解析失败）→ 在 history 注入 `Observation: 格式错误，请严格遵循 ... 格式` 继续循环，直到 `max_steps` | v0.1 | `react_agent.py` |
| A3 | LLM 抛 `LLMError` → Agent 终止本次 run，返回 `f"[ERROR] {e.user_message}"`，并记录 history | v0.1 | `agent.py` 基类 |
| A4 | 工具返回 `success=False` → Agent 把 `content`（含 `[ERROR] ...`）作为 Observation 喂回 LLM，让 LLM 自决是否换工具 | v0.1 | `react_agent.py` |
| A5 | 每次 `Agent.run()` 生成新的 `run_id = uuid.uuid4().hex[:8]`，全 Span / 日志可关联 | C 阶段 | `agent.py` 基类 |

#### 3.7.4 幂等与缓存

| # | 约束 | v0.x 起 |
|---|------|---------|
| I1 | `SearchTool.run({"query": q})` 同一 q 5s 内走内存缓存，不重复发 HTTP | v0.3 起 (D7) |

#### 3.7.5 并发与上下文隔离

- `Tracer` 用 `contextvars` 保存当前 trace（v0.3 起，D1 引入）→ 多线程 / async 不串 trace。
- v0.1 全部**同步接口优先**；async 接口放 v0.4+（与 Memory 一并引入）。
- Registry 热插拔只影响**新建** Agent 或**下一次** `run()`，不修改正在执行中的调用链。

#### 3.7.6 安全与隐私

- Trace / 日志默认脱敏：API Key、Authorization、Cookie、password、secret、token 等字段不得明文写入（v0.3 起 Tracer 实现脱敏过滤器；v0.1/v0.2 只在工具层做基础脱敏）。
- `LLMResponse.raw` 和 `ToolResult.metadata` 默认不导出 JSON；仅 `Config.debug=True` 时导出。
- 用户可见错误用 `user_message`，开发者调试信息用 `debug_message`（C2 升级双字段后强制）。
- v0.1 不内置 `TerminalTool`；E5 引入时默认只允许 `read/list`，写入/删除/执行命令独立开关。
- 外部工具默认 allowlist 注册（v0.3 D6 引入 MCP 时强制）。  <!-- 版本与上文 D 阶段对齐 -->

---
