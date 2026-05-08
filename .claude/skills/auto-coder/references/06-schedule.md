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

#### 阶段 A — 工程骨架 + LLM 可插拔 + 工具可插拔

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| A1 | 初始化目录树 | [x] | 2026-05-07 | pyproject.toml + 目录骨架 + .env.example；build-backend 已统一为 `setuptools.build_meta` |
| A2 | 引入测试框架 | [x] | 2026-05-07 | tests/ 目录 + smoke tests |
| A3 | .env 配置加载 | [x] | 2026-05-07 | Config 类 + from_env + validate |
| A4 | LLMProvider 基类 + Registry | [x] | 2026-05-07 | LLMResponse/Chunk + ABC + Registry |
| A5 | AgentLLM 门面 + 配置驱动 | [x] | 2026-05-07 | PROVIDER_CONFIG + invoke/stream；已支持 `class` 字段 lazy-load + auto-register |
| A6 | OpenAIProvider | [x] | 2026-05-07 | chat + chat_stream + LLMError；client 在 `__init__` 创建并复用，支持 timeout |
| A7 | Tool + ToolRegistry | [x] | 2026-05-07 | Tool基类 + 生命周期管理（含 enable/disable，超出 spec 原计划） |
| A8 | CalculatorTool + SearchTool | [x] | 2026-05-07 | AST安全解析 + Tavily/SerpApi；常量/函数表分离，默认后端 `tavily` |

#### 阶段 B — Agent 范式实现

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| B1 | Agent 基类 + Message 系统 | [x] | 2026-05-07 | 已提交：Agent ABC + Message(BaseModel) + history 基础能力 |
| B2 | SimpleAgent | [x] | 2026-05-07 | Prompt 约束式工具调用 `[TOOL_CALL:name:params]` |
| B3 | ReActAgent | [x] | 2026-05-07 | Thought→Action→Observation 循环，`Action: Finish[answer]` 终止 |
| B4 | PlanAndSolveAgent | [ ] | | v0.2+ |
| B5 | ReflectionAgent | [ ] | | v0.2+ |
| B6 | FunctionCallAgent | [ ] | | v0.2+ |

#### 阶段 C — 框架化加固

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| C1 | 框架目录骨架 | [x] | 2026-05-07 | 补充 kagent/__init__.py 导出 SimpleAgent/ReActAgent，全量 import 验证 |
| C2 | Config 类 + 异常体系 | [x] | 2026-05-07 | KagentError 升级双字段 user_message/debug_message，向后兼容 |
| C3 | Agent 基类框架化 | [ ] | | |
| C4 | AgentLLM 框架化（多 Provider） | [ ] | | |
| C5 | ToolRegistry 框架化（双注册 + 裸函数拔除） | [ ] | | v0.2：不含加锁；加锁归 D7 |
| C6 | SimpleAgent 框架化 | [ ] | | |
| C7 | ReActAgent 框架化 | [ ] | | |
| C8 | pip install 验证 | [ ] | | |
| C9 | FunctionCallAgent 框架化 | [ ] | | |

#### 阶段 D — MCP 外部网关 + 链路追踪 + 容错 + 监控

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| D1 | Span + Tracer 数据模型 | [ ] | | |
| D2 | TraceExporter | [ ] | | |
| D3 | Agent 埋点集成 | [ ] | | |
| D4 | MCPTool | [ ] | | |
| D5 | MCP Server 模板 | [ ] | | |
| D6 | MCP + ToolRegistry 集成 | [ ] | | |
| D7 | 容错机制 | [ ] | | |
| D8 | 监控（日志 + trace_id + Token） | [ ] | | |

#### 阶段 E — 记忆系统 + 上下文工程

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| E1 | Memory 基类 + MemoryManager | [ ] | | |
| E2 | WorkingMemory + EpisodicMemory | [ ] | | |
| E2.5 | SemanticMemory | [ ] | | v0.4 可选 |
| E3 | MemoryTool | [ ] | | |
| E4 | ContextBuilder | [ ] | | |
| E5 | NoteTool + TerminalTool | [ ] | | |

#### 阶段 F — 端到端验收

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| F1 | 旅行助手骨架 | [ ] | | |
| F2 | 深度研究骨架 | [ ] | | |
| F3 | 赛博小镇骨架 | [ ] | | |

### 6.3 详细任务

> **任务粒度说明**：本 spec 中每个任务设计为 ~1h（含测试 → 实现 → 验收），适合排期估算。在 `writing-plans` 阶段，每个任务将进一步拆分为 2-5 分钟的 bite-sized steps（写失败的测试 → 跑测试确认失败 → 写最小实现 → 跑测试通过 → commit），符合 Superpowers TDD 节奏。

### A1：初始化目录树与 pyproject.toml

| 维度 | 内容 |
|------|------|
| 目标 | 创建 `kagent/` 目录骨架、`pyproject.toml`（含依赖）、`.env.example`、所有 `__init__.py`、创建 `.venv` 虚拟环境并安装依赖 |
| 文件 | `pyproject.toml` `.env.example` `.gitignore`（含 `.venv/`、`.env`、`.env.*`、`__pycache__/`、`*.egg-info/`、`dist/`、`build/`） 以及 §5.2 目录树中所有 ★ 标记的 `__init__.py`（核心：`kagent/__init__.py`、`kagent/core/__init__.py`、`kagent/agents/__init__.py`、`kagent/tools/__init__.py`、`kagent/tools/builtin/__init__.py`、`kagent/memory/__init__.py`（占位）、`kagent/context/__init__.py`（占位）） |
| pyproject.toml | 严格按 §3.0 v0.1 pyproject 模板声明：`build-backend = "setuptools.build_meta"`（**不要写 `setuptools.backends._legacy:_Backend`，会让干净环境的 pip install 失败**）；只有 3 个核心依赖 + dev extra |
| .env.example | 严格按 §5.4 v0.1 字段清单：`LLM_PROVIDER` / `LLM_MODEL_ID` / `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_TIMEOUT` / `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` / `MAX_STEPS` / `MAX_HISTORY_LENGTH` / `SEARCH_BACKEND` / `TAVILY_API_KEY` / `SERPAPI_API_KEY` / `DEBUG` / `LOG_LEVEL`。所有字段都必须能被 `Config.from_env()` 读取（A3 任务负责字段映射） |
| 依赖 | 无（项目起点） |
| 验收 | `python -m venv .venv && .venv/Scripts/activate && pip install -e ".[dev]"` 成功（Windows）/ `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` 成功（Unix） `python -c "import kagent"` 不报错 `python -c "import kagent.memory; import kagent.context"` 不报错（占位包可导入） `python -m compileall kagent/` 通过 `pyproject.toml` 与 §3.0 模板逐字段一致 |
| 测试 | A1 不写测试，A2 引入 pytest 时再加 smoke test |


### A2：引入测试框架

| 维度 | 内容 |
|------|------|
| 目标 | 创建 `tests/` 目录、pytest 配置、冒烟测试 |
| 文件 | `pyproject.toml`（添加 `[tool.pytest.ini_options]`） `tests/__init__.py` `tests/unit/__init__.py` `tests/integration/__init__.py` `tests/unit/test_smoke.py` `tests/fixtures/.env.test` |
| 依赖 | A1 |
| 类/函数 | `test_import()` — 验证 `import kagent` 成功 `test_import_submodules()` — 验证占位包 `kagent.memory` / `kagent.context` 可导入 |
| 验收 | `pytest -q` 通过冒烟测试 |
| 测试 | `pytest -q tests/unit/test_smoke.py` |


### A3：.env 配置加载

| 维度 | 内容 |
|------|------|
| 目标 | 实现 `Config` 类，从 `.env` 文件 + 环境变量读取所有配置，必填字段校验 |
| 文件 | `kagent/core/config.py` `kagent/core/exceptions.py`（仅 `ConfigError` 占位，C2 再升级双字段） |
| 依赖 | A1 |
| 类/函数 | `Config` (Pydantic BaseModel) — 字段对应 §5.4 v0.1 .env 清单：`default_provider`/`default_model`/`api_key`/`base_url`/`timeout`/`temperature`/`max_tokens`/`debug`/`log_level`/`max_history_length`/`max_steps`。`Config.from_env(env_file=None)` — 优先读 `.env` 文件（dotenv）→ 再读 process env → 实例化 → `validate_config()`。`validate_config()` — 校验 `LLM_API_KEY` 非空（ollama/vllm 除外）。`load_config()` 便捷函数。 |
| 验收 | `Config.from_env()` 在有 `.env` 文件时返回有效 Config 实例 缺 `LLM_API_KEY` 且 Provider 非 ollama/vllm → 抛 `ConfigError` 含可读中文消息 `Config().debug == False` 默认值正确 `Config.from_env().model_dump()` 返回完整字典 数值字段（`max_steps` / `temperature`）格式错误时抛 `ValueError`（pydantic 校验） |
| 测试 | `pytest -q tests/unit/test_config.py` |


### A4：LLMProvider 基类 + LLMProviderRegistry

| 维度 | 内容 |
|------|------|
| 目标 | 定义 LLM Provider 的抽象接口和注册中心 |
| 文件 | `kagent/core/llm/models.py`（`LLMResponse` / `LLMChunk`）+ `kagent/core/llm/base.py`（`LLMProvider` / `LLMProviderRegistry`）+ `kagent/core/llm/__init__.py`（导出） |
| 依赖 | A1, A2 |
| 类/函数 | `LLMResponse(BaseModel)` / `LLMChunk(BaseModel)` `LLMProvider(ABC)` — `chat(messages, model, temperature, tools=None, tool_choice=None) -> LLMResponse` / `chat_stream(...) -> Iterator[LLMChunk]` `LLMProviderRegistry` — `register(name, provider)` / `get(name)` / `list_providers()` |
| 验收 | `LLMProvider()` 不能直接实例化 `registry.register("test", mock_provider)` 后 `registry.get("test")` 返回 mock_provider `registry.get("nonexistent")` 抛 `ValueError`（错误信息含可用 provider 列表） `registry.register("x", "not a provider")` 抛 `TypeError` |
| 测试 | `pytest -q tests/unit/test_llm.py -k "TestLLMProvider or TestLLMProviderRegistry"` |


### A5：AgentLLM 门面 + 配置驱动选择（含 lazy-load）

| 维度 | 内容 |
|------|------|
| 目标 | 实现 `AgentLLM` 类，从配置读取 Provider 名称并自动选择；**当 provider 未注册时通过 PROVIDER_CONFIG[name].class 反射 lazy-load 并自动 register**，让 `AgentLLM()` 真正开箱即用 |
| 文件 | `kagent/core/llm/factory.py`（`AgentLLM` + `PROVIDER_CONFIG` + lazy-load 逻辑）+ `kagent/core/llm/__init__.py`（导出） |
| 依赖 | A3 (Config), A4 (Registry) |
| 类/函数 | `PROVIDER_CONFIG` 配置字典（含 `class` 字段，例如 `"class": "kagent.core.llm.providers.OpenAIProvider"`）。`AgentLLM.__init__(provider=None, model=None, api_key=None, base_url=None, timeout=60, config=None)`。`AgentLLM.register_provider(name, provider)` 类方法。`AgentLLM._get_or_load_provider()` — 先查 registry，未注册则查 PROVIDER_CONFIG，反射 import + 实例化 + register，仍失败抛 `ConfigError`。`AgentLLM.invoke(messages, temperature, tools=None, tool_choice=None) -> LLMResponse`。`AgentLLM.stream(messages, temperature, tools=None) -> Iterator[LLMChunk]`。 |
| 验收 | `AgentLLM(config=Config(api_key="sk-test"))` **不需要预先 `register_provider`** 即可创建（自动 lazy-load OpenAIProvider）。`AgentLLM()` 从 `LLM_PROVIDER` env 读取 provider 名。`AgentLLM.register_provider("test", mock)` 后 `AgentLLM(provider="test")` 优先使用已注册实例（不再 lazy-load）。`provider="unknown"` 且 PROVIDER_CONFIG 无该项 → 抛 `ConfigError`。explicit api_key/base_url/timeout 覆盖 Config 字段并被 lazy-load 出来的 provider 实例使用。 |
| 测试 | `pytest -q tests/unit/test_llm.py -k "TestAgentLLMInit or TestAgentLLMInvoke or test_lazy_load"` |


### A6：OpenAIProvider（可插拔 Provider 示例实现）

| 维度 | 内容 |
|------|------|
| 目标 | 实现首个具体 Provider，验证 A4/A5 的可插拔架构可用：实现 `LLMProvider` 接口 → 由 A5 的 lazy-load 自动注册 → 改 `.env` 一行配置即可切换。OpenAI 兼容接口作为 v0.1 MVP 的默认实现，但架构上不绑定任何特定服务商 |
| 文件 | `kagent/core/llm/providers.py`（`OpenAIProvider`）+ `kagent/core/llm/__init__.py`（导出） |
| 依赖 | A4 (LLMProvider 基类) |
| 类/函数 | `OpenAIProvider(api_key, base_url, timeout=60)` — 实现 `LLMProvider.chat() -> LLMResponse` + `chat_stream() -> Iterator[LLMChunk]`。**构造函数里建一次 `self._client = OpenAI(api_key=..., base_url=..., timeout=timeout)`，chat/stream 复用该 client，不再每次 new**。构造参数由 A5 的 lazy-load 从 `PROVIDER_CONFIG` + `Config` 自动注入，用户无需手写 |
| 验收 | Mock OpenAI API 响应 → `provider.chat()` 返回 `LLMResponse(content="...")`。`provider.chat_stream()` yield 多个 `LLMChunk`。任意异常（含超时）→ 包装为 `LLMError` 抛出（A 阶段单字段，C2 升级双字段）。tool_calls 字段被正确提取（id / function.name / function.arguments）。client 实例只在 `__init__` 创建一次（性能 + 连接池）。可插拔验证：实现一个 `OllamaProvider(LLMProvider)` 并加进 `PROVIDER_CONFIG`，仅靠改 `.env` 的 `LLM_PROVIDER` 即可切换，Agent 代码零改动 |
| 测试 | `pytest -q tests/unit/test_llm.py -k "TestOpenAIProvider"` |

> **可插拔验证**：A6 的核心价值是证明"写一个类 + 一行 PROVIDER_CONFIG = 接入新服务商"的架构可行。OllamaProvider / ZhipuProvider / VLLMProvider 等在 C4 实现，但只需实现 `LLMProvider` 接口 + 在 `PROVIDER_CONFIG` 中加一行映射即可，Agent 层代码零改动。


### A7：Tool 基类 + ToolRegistry（含 lifecycle）

| 维度 | 内容 |
|------|------|
| 目标 | 定义 Tool 抽象接口和可插拔注册中心，支持运行时 enable/disable |
| 文件 | `kagent/tools/base.py` `kagent/tools/registry.py` `kagent/tools/__init__.py`（导出） |
| 依赖 | A1 |
| 类/函数 | `ToolResult(BaseModel)` — `content`, `success`, `error`, `metadata` `ToolParameter(BaseModel)` — `name`, `type`, `description`, `required`, `default` `Tool(ABC)` — `run(parameters) -> ToolResult` / `get_parameters() -> list[ToolParameter]` / `to_openai_schema()`（v0.1 提前实现，B6 / C9 复用） `ToolRegistry` — 注册：`register_tool(tool)` / `register_function(name, desc, func, parameters=None)` / `unregister(name)`；lifecycle：`disable(name)` / `enable(name)` / `is_enabled(name)` / `is_registered(name)`；执行：`execute_tool(name, arguments) -> ToolResult`（按 §3.7 T1-T3 永远不抛）；自省：`list_tools() -> dict` / `get_tools_description() -> str`（用于注入 Prompt） |
| 验收 | `Tool()` 不能直接实例化 `register_function("echo", "...", lambda a: a["text"])` 后 `execute_tool("echo", {"text":"hi"})` 返回 `ToolResult(success=True, content="hi")` `unregister("echo")` 后再 execute → `success=False, content` 含 "未注册" `disable("calc")` 后 execute → `success=False, content` 含 "已被禁用"；`enable("calc")` 后恢复 `get_tools_description()` 不包含已 disable 的工具 工具内部抛 `ValueError` → `execute_tool` 返回 `success=False`，**不向上抛**（§3.7 T3） |
| 测试 | `pytest -q tests/unit/test_tools.py -k "TestTool* or TestToolRegistry or TestToolLifecycle"` |


### A8：CalculatorTool + SearchTool

| 维度 | 内容 |
|------|------|
| 目标 | 实现两个内置工具作为 Tool 子类示例 |
| 文件 | `kagent/tools/builtin/calculator.py` `kagent/tools/builtin/search.py` `kagent/tools/builtin/__init__.py`（导出） |
| 依赖 | A7 (Tool 基类) |
| 类/函数 | **CalculatorTool(Tool)** — `run({"expression": "2+3*4"}) -> ToolResult`，用 `ast` 安全解析。常量与函数表分离：`_CONSTANTS = {"pi": math.pi, "e": math.e}`（被 `ast.Name` 解析），`_FUNCTIONS = {"sqrt", "sin", "cos", "tan", "log", "log10", "log2", "exp", "abs", "round", "min", "max", "pow"}`（被 `ast.Call` 解析）。**不要把 pi/e 也注册成函数**（避免 `pi()` 这种奇怪写法）。`SearchTool(Tool)` — v0.1 使用单一搜索后端，**默认 `SEARCH_BACKEND=tavily`**（与 .env.example 一致），Tavily 依赖 `tavily-python>=0.3`，SerpApi 备用后端用标准库 `urllib.request`；由 `SEARCH_BACKEND` env + 对应 API Key 决定后端，不做降级链 |
| 验收 | `calculator.run({"expression": "2+3*4"}).content == "14"`；`sqrt(16)` → `"4.0"`；`sin(pi/2)` → `"1.0"`（pi 作为常量）；`pi()` → 失败（"不支持的函数: pi"）；`1/0` → `success=False, content` 含 "除数不能为零"。`search.run({"query": "Python"})` 返回 `ToolResult(success=True, content=非空)`（需配置 API Key）；未配置 API Key → 返回 `ToolResult(success=False, content="[ERROR] 搜索 API Key 未配置，请在 .env 中设置 ..."`） |
| 测试 | `pytest -q tests/unit/test_tools.py -k "TestCalculatorTool or TestSearchTool"` |


### B1：Agent 基类 + Message 系统

| 维度 | 内容 |
|------|------|
| 目标 | 定义所有 Agent 的统一接口和消息格式 |
| 文件 | `kagent/core/agent.py` `kagent/core/message.py` `kagent/core/__init__.py`（导出 `Agent` / `Message`） |
| 依赖 | A4 (LLMProvider 用于类型注解), A5 (AgentLLM) |
| 类/函数 | `Message(BaseModel)` — `content` / `role: Literal["user","assistant","system","tool"]` / `timestamp: datetime`（默认 `datetime.now(timezone.utc)`）/ `metadata: Optional[dict]` / `to_dict() -> {"role": ..., "content": ...}` `Agent(ABC)` — `__init__(name, llm, system_prompt=None, config=None)`（config 默认 `Config()`）/ `@abstractmethod run(input_text, **kwargs) -> str` / `add_message(message)`（按 `config.max_history_length` 自动 trim）/ `clear_history()` / `get_history()`（返回 history 副本，避免外部修改） |
| 验收 | `Agent()` 不能直接实例化 `Message("hi","user").to_dict() == {"role":"user","content":"hi"}` 非法 role → pydantic 抛 `ValidationError` 添加 N+1 条消息（N=`max_history_length`）→ history 长度等于 N 且只保留最新 `get_history()` 返回的 list 修改不影响内部 history |
| 测试 | `pytest -q tests/unit/test_message.py tests/unit/test_agent.py -k "TestMessage or TestAgentIsAbstract or TestAgentInit or TestAgentHistory"` |


### B2：SimpleAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现基础对话 Agent，支持可选工具调用（基于 Prompt 约束式工具调用，与 OpenAI 原生 function calling 解耦） |
| 文件 | `kagent/agents/simple_agent.py` `kagent/agents/__init__.py`（导出） |
| 依赖 | B1, A5 (AgentLLM), A7 (ToolRegistry) |
| 类/函数 | `SimpleAgent(Agent)` — `__init__(name, llm, system_prompt=None, config=None, tool_registry: ToolRegistry | None = None)` `run(input_text, max_steps=None) -> str`（`max_steps` 默认从 config 取） `_run_with_tools(messages, max_steps)` — 循环 LLM + 工具 `_parse_tool_calls(text) -> list[dict]` — 正则匹配 `[TOOL_CALL:name:params]`，捕获 0~N 个 `_execute_tool_call(tool_name, parameters_str) -> ToolResult` — 调 ToolRegistry，按 §3.7 T1-T3 处理 `add_tool(tool)` / `remove_tool(name)` / `stream_run(input_text)` |
| 工具调用格式 | `[TOOL_CALL:name:params]`，`params` 为字符串，对内置工具默认包装为 `{"query": params}` 或 `{"expression": params}`（约定见 ReActAgent） |
| 验收 | 无工具时 `run("hi")` 直接返回 mock LLM 响应 LLM 返回 `[TOOL_CALL:calculator:1+1]` → 解析 → 执行 CalculatorTool → Observation 注入 → 二次 LLM 调用 → 返回最终答案 工具不存在时（已被 unregister）→ Observation 含 "未注册"，循环继续，不抛异常 `max_steps` 超过 → 强制返回当前最佳答案，不抛异常（§3.7 A1） |
| 测试 | `pytest -q tests/unit/test_agent.py -k "TestSimpleAgent"` |


### B3：ReActAgent

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Thought→Action→Observation 循环 |
| 文件 | `kagent/agents/react_agent.py` `kagent/agents/__init__.py`（导出） |
| 依赖 | B1, A5, A7, A8 |
| 类/函数 | `ReActAgent(Agent)` — `__init__(name, llm, system_prompt=None, config=None, tool_registry=None)` `run(input_text, max_steps=None) -> str` `_parse_output(text) -> (thought: str | None, action: str | None)` — 正则匹配 `Thought:...\nAction:...` `_parse_action(action_text) -> (tool_name: str, tool_input: str)` — 解析 `ToolName[params]` `_format_prompt(input_text)` — 注入 `{tools}` `{history}` `{input}` |
| Action 格式 | **`Action: ToolName[parameters]`** — 调用工具。`parameters` 为字符串，按工具名做参数包装：`Calculator` → `{"expression": params}`，`Search` → `{"query": params}`，其他 → `{"query": params}`（默认）。**`Action: Finish[最终答案]`** — 终止循环，返回 `最终答案`（去掉中括号）。示例：`Action: Search[北京天气]` / `Action: Calculator[25 * 9/5 + 32]` / `Action: Finish[北京今天晴，25°C]` |
| 容错 | LLM 输出无 `Action:` → history 注入 `Observation: 格式错误，请严格遵循 Thought/Action 格式` 继续循环（§3.7 A2） 工具返回 `success=False` → `[ERROR] ...` 作为 Observation 喂回 LLM（§3.7 A4） |
| 验收 | Mock LLM 返回 `Action: Finish[答案]` → `run()` 返回 `"答案"` Mock LLM 返回 `Action: Search[query]` → 调 SearchTool → Observation 注入 → 继续循环 达到 `max_steps` → 不抛异常，返回当前最佳答案 LLM 返回纯文本无 `Action:` → 循环继续注入错误提示，最终在 max_steps 时返回 |
| 测试 | `pytest -q tests/unit/test_agent.py -k "TestReActAgent"` |


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
| 目标 | 验证 A1 创建的目录树与 §5.2 一致，补充遗漏的 `__init__.py`，确保 `python -m compileall kagent/` 通过，确保所有顶层符号可从 `kagent` 直接 import |
| 文件 | 检查并补充：`kagent/__init__.py`（顶层导出 SimpleAgent / ReActAgent / AgentLLM / Config / Message / KagentError 等）、`kagent/core/__init__.py`、`kagent/agents/__init__.py`、`kagent/tools/__init__.py` |
| 依赖 | A1-A8, B1-B3 |
| 类/函数 | 无新增逻辑，仅补 `__all__` 与 re-export |
| 验收 | `python -m compileall kagent/` 通过 `python -c "from kagent import SimpleAgent, ReActAgent, AgentLLM, Config, Message, KagentError, LLMError, AgentError, ToolError, ConfigError; print('OK')"` 输出 `OK` `python -c "import kagent.memory; import kagent.context"` 占位包可导入 |
| 测试 | `pytest -q tests/integration/test_framework_import.py`（C8 创建） |


### C2：异常体系升级为双字段 user_message / debug_message

| 维度 | 内容 |
|------|------|
| 目标 | 把 A 阶段引入的单字段 `KagentError(message)` 升级为双字段 `KagentError(user_message, debug_message=None)`，**保持向后兼容**（老代码 `LLMError("foo")` 自动落入 `user_message="foo"`），并迁移所有现存 raise 处使用合适字段 |
| 文件 | `kagent/core/exceptions.py`（升级 `__init__`） 全 repo 各 raise 处（按需补 `debug_message`） |
| 依赖 | A3 (已有 ConfigError), A6 (已有 LLMError), B3 |
| 类/函数 | `KagentError.__init__(self, user_message: str, debug_message: str | None = None)` `__str__` 默认返回 user_message `AgentError` / `LLMError` / `ToolError` / `ConfigError` 全部继承不重写 |
| 验收 | `LLMError("旧式")` 仍然合法，`.user_message == "旧式"`, `.debug_message is None` `LLMError(user_message="LLM 调用失败", debug_message="HTTP 503: ...")` 双字段都可访问 `KagentError.__str__` 返回 user_message（不暴露 debug_message） A 阶段已有的所有测试（`tests/unit/test_*.py`）继续全部通过（向后兼容验证） |
| 测试 | `pytest -q tests/unit/test_exceptions.py` + 全量回归 `pytest -q` |


### C3：Agent 基类框架化（注入 custom_prompt + run_id）

| 维度 | 内容 |
|------|------|
| 目标 | B1 的 Agent 基类已在 `kagent/core/agent.py`，本任务**不移动文件、不动 history 逻辑**——只给已有 Agent 基类注入：`custom_prompt` 模板变量、`run_id` 属性 |
| 文件 | `kagent/core/agent.py`（修改） |
| 依赖 | B1, A3 (Config, B1 已用) |
| 类/函数 | `Agent.__init__` 增加 `custom_prompt: str | None = None` 字段；新增 `run_id` 属性 — `uuid.uuid4().hex[:8]`，**每次 `run()` 调用前由子类负责重置**（基类提供 `_new_run_id()` 工具方法） `Agent._format_prompt(template, **vars)` 工具方法：替换 `{tools}` `{history}` `{input}` `{max_steps}` 等模板变量；子类可补充自己的变量 |
| 模板变量 | `{tools}` — `tool_registry.get_tools_description()`； `{history}` — `\n`.join(`m.to_dict()` 字符串化)； `{input}` — 当前用户输入； `{max_steps}` — config.max_steps；子类可追加（如 ReAct 的 `{thought_format}`） |
| 验收 | `agent = SimpleAgent(name="t", llm=mock_llm, config=Config(api_key="x"), custom_prompt="{tools}\n{input}")` 创建成功 `agent.custom_prompt` 字符串中的 `{input}` 被实际 input 替换 同一 agent 多次 `run()`，每次 `agent.run_id` 不同（`_new_run_id` 在 run 起始调用） |
| 测试 | `pytest -q tests/unit/test_agent.py -k "TestAgentCustomPrompt or TestAgentRunId"` |


### C4：AgentLLM 框架化（多 Provider + 自动检测）

| 维度 | 内容 |
|------|------|
| 目标 | 升级 AgentLLM，增加 Ollama/VLLM（OpenAI 兼容，复用 `OpenAIProvider`）已在 A5 PROVIDER_CONFIG 中映射；本任务新增 `Zhipu` 和 `ModelScope` 两个独立 Provider 子类 + `auto` 自动检测策略 |
| 文件 | `kagent/core/llm/providers.py`（新增 `ZhipuProvider` / `ModelScopeProvider`） `kagent/core/llm/factory.py`（PROVIDER_CONFIG 扩充 + `_auto_detect()` 方法） |
| 依赖 | A5, A6 |
| 类/函数 | 新增 `ZhipuProvider(LLMProvider)`、`ModelScopeProvider(LLMProvider)`（如二者也走 OpenAI 兼容协议，可继承 `OpenAIProvider` 仅覆盖默认 base_url） `AgentLLM._auto_detect(config) -> str` — 启发式：① `LLM_BASE_URL` 含 `localhost:11434` → ollama；② `LLM_BASE_URL` 含 `bigmodel.cn` → zhipu；③ `LLM_BASE_URL` 含 `modelscope.cn` → modelscope；④ 否则 openai。`PROVIDER_CONFIG` 加 `zhipu` / `modelscope` 行 |
| 验收 | `LLM_PROVIDER=auto` + `LLM_BASE_URL=http://localhost:11434/v1` → 自动选择 ollama `LLM_PROVIDER=auto` + 默认 base_url → openai 显式 `LLM_PROVIDER=zhipu` → 走 Zhipu 路径 |
| 测试 | `pytest -q tests/unit/test_llm.py -k "TestAutoDetect or TestZhipuProvider"` |


### C5：ToolRegistry 框架化（双注册 + 拔除）

| 维度 | 内容 |
|------|------|
| 目标 | 升级 ToolRegistry 支持 Tool 对象 + 裸函数双重注册 |
| 文件 | `kagent/tools/registry.py` |
| 类/函数 | `ToolRegistry._tools: dict` + `ToolRegistry._functions: dict` `register_tool(tool: Tool)` / `register_function(name, desc, func)` / `unregister(name)` 同时移除两类来源；`get_tools_description()` — 合并两种来源 |
| 边界 | 本任务不做并发加锁；`threading.Lock` 属于 D7 容错增量 |
| 验收 | 同时注册 Tool 对象和裸函数 → `get_tools_description()` 包含两者；`unregister` 后 description 不包含该工具，且后续 `execute_tool` 返回未注册错误 |
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


### C8：pip install 验证 + 最小 README

| 维度 | 内容 |
|------|------|
| 目标 | 在干净环境下 `pip install -e ".[dev]"` 可安装；`from kagent import ...` 全量 import 可用；README 提供最小可读说明 |
| 文件 | `pyproject.toml`（确保 `build-backend = "setuptools.build_meta"`） `README.md`（最少：项目定位 / pip install / 一段 quickstart 代码 / v0.1 范围说明 / 链接到 DEV_SPEC.md） `tests/integration/test_framework_import.py` `tests/integration/test_pip_install.py` |
| 依赖 | C1, C2, C3 |
| 类/函数 | `test_all_exports` — 验证 `from kagent import SimpleAgent, ReActAgent, AgentLLM, Config, Message, KagentError, LLMError, AgentError, ToolError, ConfigError` 全部可用 `test_editable_install` — `subprocess.run(["pip", "install", "-e", "."])` 成功（CI 中可 mark external 跳过） |
| 验收 | 干净 venv 下 `pip install -e ".[dev]"` 成功（不依赖现有 .venv 已编译产物） `python -c "from kagent import SimpleAgent, AgentLLM, Config; print('OK')"` 输出 `OK` `pytest -q` 全量通过 README 含 quickstart：`from kagent import SimpleAgent, AgentLLM, Config; ...`（10 行内可跑） |
| 测试 | `pytest -q tests/integration/test_framework_import.py tests/integration/test_pip_install.py` |


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
| 文件 | `kagent/core/tracing/models.py`（`Span` / `SpanType` / `SpanStatus`）+ `kagent/core/tracing/tracer.py`（`Tracer`）+ `kagent/core/tracing/__init__.py`（导出） |
| 依赖 | C2 (KagentError 双字段) |
| 类/函数 | `SpanStatus(str, Enum)` — OK / ERROR `SpanType(str, Enum)` — AGENT_RUN / AGENT_STEP / LLM_CALL / TOOL_CALL `Span` (dataclass) — 所有字段见 3.4 `Tracer` (单例 + `contextvars` 并发隔离) — `start_trace()` / `start_span()` / `end_span()` / `span()` context manager / `add_event()` / `get_current_trace()` / `get_all_traces()` / `clear()` |
| 验收 | `start_trace → start_span → end_span → end_span` 生成正确 parent/children 树 context manager 自动处理异常并记 `status=ERROR` `duration_ms` 自动计算 多线程/async 场景下不串 trace（contextvars） |
| 测试 | `pytest -q tests/unit/test_tracing.py -k "TestTracer"` |


### D2：TraceExporter

| 维度 | 内容 |
|------|------|
| 目标 | 实现 Trace 树的导出（dict / JSON / 终端树形图） |
| 文件 | `kagent/core/tracing/exporter.py`（`TraceExporter`）+ `kagent/core/tracing/__init__.py`（导出） |
| 依赖 | D1 |
| 类/函数 | `TraceExporter.to_dict(span) -> dict` — 递归 `TraceExporter.to_json(span, indent) -> str` `TraceExporter.to_tree(span, indent) -> str` — 终端树形输出 |
| 验收 | `to_dict` 包含所有字段且 children 递归 `to_json` 可解析回 dict 顶层含 `total_tokens` / `total_duration_ms` 汇总 `to_tree` 输出包含 span name + duration_ms |
| 测试 | `pytest -q tests/unit/test_tracing.py -k "TestExporter"` |


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


### D7：容错机制（v0.1 之上的增量加固）

| 维度 | 内容 |
|------|------|
| 目标 | 把 §3.7 中标 "v0.3 起 (D7)" 的约束逐项落地：LLM 重试（L3）、ToolRegistry 加锁（T5）、SearchTool 缓存（I1）、MCP 重连。是 v0.1/v0.2 fail-fast 行为之上的增量加固，**不重复定义已在 v0.1 实现的工具异常处理（T3）**。 |
| 文件 | `kagent/tools/registry.py`（加 `threading.Lock`）`kagent/tools/mcp_tool.py`（重连）`kagent/agents/react_agent.py`（注入解析错误 Observation） `kagent/agents/function_call_agent.py`（API 重试） `kagent/tools/builtin/search.py`（5s 缓存） |
| 依赖 | C2 (KagentError 双字段), D1-D3 (Tracer 埋点 retry 事件) |
| 类/函数 | `ToolRegistry`：注册/注销加锁（T5）；`MCPTool.call_tool()`：子进程断开时自动重连（最多 3 次），超时 30s；`ReActAgent.run()`：解析失败注入 `"Observation: 格式错误..."`（A2 已在 v0.1）→ 这里只补 Trace 上的 `add_event("error", ...)`；`FunctionCallAgent._invoke_with_tools()`：超时/429 → 指数退避重试 1s→2s→4s 最多 3 次（L3）；`SearchTool.run()`：同 query 5s 内走 LRU 缓存（I1）。 |
| 验收 | MCP Server 进程被 kill → MCPTool 自动重连，Agent 无感知 LLM API 返回 429 → 退避重试，3 次均失败抛 `LLMError(user_message=...)` 含中文消息 同一 query 5s 内重复 search → 第二次从缓存返回，HTTP 调用次数 = 1 工具执行抛 `ValueError`（v0.1 已经做过的）→ Agent 收到 `ToolResult(success=False)` 不中断循环（不重复测，仅作回归断言） |
| 测试 | `pytest -q tests/unit/test_fault_tolerance.py` |


### D8：监控（请求级日志 + trace_id + Token 用量统计）

| 维度 | 内容 |
|------|------|
| 目标 | 为每次 Agent 运行建立结构化日志（含 trace_id）、统计 Token 消耗 |
| 文件 | `kagent/core/tracing/tracer.py` `kagent/core/tracing/exporter.py` `kagent/core/llm/factory.py` `kagent/core/agent.py` |
| 依赖 | D1, D3, C3 |
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


### E2.5：SemanticMemory（v0.4 可选）

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

