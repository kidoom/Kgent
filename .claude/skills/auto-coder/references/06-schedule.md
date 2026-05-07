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
| A1 | 初始化目录树 | [x] | 2026-05-07 | |
| A2 | 引入测试框架 | [ ] | | |
| A3 | .env 配置加载 | [ ] | | |
| A4 | LLMProvider 基类 + Registry | [ ] | | |
| A5 | AgentLLM 门面 + 配置驱动 | [ ] | | |
| A6 | OpenAIProvider | [ ] | | |
| A7 | Tool + ToolRegistry | [ ] | | |
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
| 文件 | `pyproject.toml` `.env.example` `.gitignore`（含 `.venv/`、`.env`、`__pycache__/`） `kagent/__init__.py` `kagent/core/__init__.py` `kagent/agents/__init__.py` `kagent/tools/__init__.py` `kagent/tools/builtin/__init__.py` `kagent/memory/__init__.py` `kagent/context/__init__.py` |
| pyproject.toml 依赖 | 按 §3.0 依赖清单完整声明，不得遗漏或自行引入未列出的库 |
| .env.example | `LLM_PROVIDER=openai` `LLM_MODEL_ID=gpt-4o` `LLM_API_KEY=your-api-key-here` `LLM_BASE_URL=https://api.openai.com/v1` `LLM_TIMEOUT=60` `SEARCH_BACKEND=serpapi` `SERPAPI_API_KEY=` `TAVILY_API_KEY=` `TRACE_ENABLED=true` `TRACE_EXPORT=console` `LOG_LEVEL=INFO` `DEBUG=false` `MAX_HISTORY_LENGTH=50` `MAX_STEPS=5` |
| 验收 | `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` 成功 `python -c "import kagent"` 不报错 `python -c "import kagent.memory; import kagent.context"` 不报错 `pyproject.toml` 包含全部依赖 `pytest -q tests/unit/test_smoke.py` 通过 |
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


### A6：OpenAIProvider

| 维度 | 内容 |
|------|------|
| 目标 | 实现 OpenAI 兼容 Provider（v0.1 MVP 只需这一个 Provider） |
| 文件 | `kagent/core/llm.py` |
| 类/函数 | `OpenAIProvider(api_key, base_url, timeout)` — 实现 `LLMProvider.chat() -> LLMResponse` + `chat_stream() -> Iterator[LLMChunk]`，内部使用 `openai` SDK 的 `chat.completions.create` |
| 验收 | Mock OpenAI API 响应 → `provider.chat()` 返回 `LLMResponse(content="...")` `provider.chat_stream()` yield 多个 `LLMChunk` API 超时 → 抛 `LLMError` |
| 测试 | `pytest -q tests/unit/test_llm.py -k "test_openai_provider"` |

> **注意**：OllamaProvider / ModelScopeProvider / ZhipuProvider / VLLMProvider 属于 v0.2+（C4 任务），A6 只实现 `OpenAIProvider`。不要超前实现。


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

