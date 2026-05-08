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
                        │  → v0.2 (B4-B6 + C9)                 │
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
        │  v0.1: openai / ollama / vllm（OpenAI 兼容协议）     │
        │  v0.2: + Zhipu / ModelScope / auto-detect          │
        │  v0.3: + MCPTool（MCP 外部网关，D 阶段）             │
        └───────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────────────────────┐
        │        🧱 基础设施层 (Memory / Context — v0.4 Kagent Memory)   │
        │                                                              │
        │  Memory System / ContextBuilder / Storage（E 阶段）           │
        │  v0.1 仅创建占位包 kagent.memory / kagent.context              │
        └──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      🔍 横切关注层（贯穿所有层）                                │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   链路追踪    │  │   监控告警    │  │   容错降级    │  │ ★ 配置驱动    │    │
│  │              │  │              │  │              │  │              │    │
│  │ Tracer 单例  │  │ trace_id 贯穿 │  │ try/except   │  │ .env (v0.1)  │    │
│  │ Span 树      │  │ Token 统计   │  │ 工具异常→Result│ │ settings.yaml│    │
│  │ Tree/JSON导出│  │ 请求级日志   │  │ 指数退避重试  │  │   (v0.3+)    │    │
│  │              │  │              │  │              │  │              │    │
│  │   v0.3 (D)   │  │   v0.3 (D)   │  │ v0.1 工具部分 │  │ ★ v0.1 核心  │    │
│  │              │  │              │  │ v0.3 LLM 重试 │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                                             │
│  v0.1 仅做：① 工具异常→ToolResult(success=False) 不抛异常；                   │
│           ② Provider 不可用→ConfigError 启动期 fail-fast；                  │
│           ③ Config 驱动 Provider 切换、模型/温度/max_steps 等运行参数。       │
└─────────────────────────────────────────────────────────────────────────────┘

### 5.2 目录结构（**权威定义** — 任务卡的"文件"列必须与本表一致）

> 标记说明（与 §0.2 速查矩阵 / §1.4 后续路线一致）：
> ★ = v0.1 MVP（必做）｜◇ = v0.2 Core 增强（多 Provider + 后续 Agent 范式）｜△ = v0.3 Observability（D 阶段）｜◯ = v0.4 Memory（E 阶段）｜▽ = v0.5 Examples（F 阶段）
>
> v0.1 不创建 `config/settings.yaml` 文件；预留 `kagent/memory/` `kagent/context/` 仅放空 `__init__.py` 占位。

```
Kgent/
├── kagent/                          # 包根
│   ├── __init__.py                  ★ 顶层导出（SimpleAgent / ReActAgent / AgentLLM / Config / KagentError 等）
│   ├── core/
│   │   ├── __init__.py              ★ 统一导出 core 子模块的公开符号
│   │   ├── config.py                ★ A3 Config 类（Pydantic）+ from_env() + load_config()
│   │   ├── exceptions.py            ★ C2 KagentError / AgentError / LLMError / ToolError / ConfigError（双字段）
│   │   ├── agent.py                 ★ B1 Agent(ABC) — 单文件，不做 agent/ 子包
│   │   ├── message.py               ★ B1 Message(BaseModel)
│   │   ├── llm/                     ★ A4-A6 LLM 调用层（package）
│   │   │   ├── __init__.py          ★ 统一导出 LLM 子模块的公开符号
│   │   │   ├── models.py            ★ A4 LLMResponse + LLMChunk
│   │   │   ├── base.py              ★ A4 LLMProvider(ABC) + LLMProviderRegistry
│   │   │   ├── factory.py           ★ A5 AgentLLM + PROVIDER_CONFIG（含 lazy-load）
│   │   │   └── providers.py         ★ A6 OpenAIProvider
│   │   └── tracing/                 △ D1-D2 链路追踪（package）
│   │       ├── __init__.py          △
│   │       ├── models.py            △ Span + SpanType + SpanStatus
│   │       ├── tracer.py            △ Tracer 单例
│   │       └── exporter.py          △ TraceExporter
│   ├── agents/
│   │   ├── __init__.py              ★
│   │   ├── simple_agent.py          ★ B2 / C6 SimpleAgent
│   │   ├── react_agent.py           ★ B3 / C7 ReActAgent
│   │   ├── plan_solve_agent.py      ◇ B4 (v0.2+)
│   │   ├── reflection_agent.py      ◇ B5 (v0.2+)
│   │   └── function_call_agent.py   ◇ B6 / C9 (v0.2+)
│   ├── tools/
│   │   ├── __init__.py              ★
│   │   ├── base.py                  ★ A7 Tool + ToolParameter + ToolResult
│   │   ├── registry.py              ★ A7 ToolRegistry（含 enable/disable lifecycle）
│   │   ├── mcp_tool.py              △ D4 (v0.3)
│   │   └── builtin/
│   │       ├── __init__.py          ★
│   │       ├── calculator.py        ★ A8 CalculatorTool
│   │       └── search.py            ★ A8 SearchTool
│   ├── memory/                      ◯ v0.4，v0.1 仅 __init__.py 占位
│   │   └── __init__.py              ★（占位，无导出）
│   └── context/                     ◯ v0.4，v0.1 仅 __init__.py 占位
│       └── __init__.py              ★（占位，无导出）
├── tests/
│   ├── __init__.py                  ★
│   ├── unit/
│   │   ├── __init__.py              ★
│   │   ├── test_smoke.py            ★ A2 import 烟雾测试
│   │   ├── test_config.py           ★ A3
│   │   ├── test_llm.py              ★ A4-A6
│   │   ├── test_tools.py            ★ A7-A8
│   │   ├── test_message.py          ★ B1
│   │   ├── test_agent.py            ★ B1-B3
│   │   ├── test_exceptions.py       ★ C2
│   │   ├── test_tracing.py          △ D1-D2
│   │   ├── test_fault_tolerance.py  △ D7
│   │   ├── test_memory.py           ◯
│   │   ├── test_context.py          ◯
│   │   └── test_note_terminal.py    ◯
│   ├── integration/
│   │   ├── __init__.py              ★
│   │   ├── test_llm_tool_wire.py    ★ A 阶段集成
│   │   ├── test_agent_with_tool.py  ★ B 阶段集成（B3 后）
│   │   ├── test_framework_import.py ★ C8 import 全量验证
│   │   ├── test_pip_install.py      ★ C8 editable install 验证
│   │   ├── test_agent_with_tracing.py △ D3
│   │   ├── test_mcp.py              △ D4-D6
│   │   ├── test_memory_tool.py      ◯
│   │   └── test_context.py          ◯
│   ├── e2e/                         （v0.1 手动跑，CI 不强制）
│   │   └── test_react_agent.py      ★ 黄金测试集（手动, 真实 LLM）
│   └── fixtures/
│       └── .env.test                ★ A2
├── pyproject.toml                   ★ A1
├── .env.example                     ★ A1
├── .gitignore                       ★ A1（.venv/, .env, .env.*, __pycache__/, *.egg-info/, dist/, build/）
└── README.md                        ★ C8（v0.1 最小内容：项目定位 + pip install + quickstart）
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

#### v0.1 — 仅 `.env`（单一配置源）

```bash
# 必填
LLM_PROVIDER=openai          # openai | ollama | vllm
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=sk-xxx           # ollama / vllm 可空

# 可选（留空走 PROVIDER_CONFIG.default_base_url）
LLM_BASE_URL=
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=

# Agent 行为
MAX_STEPS=5
MAX_HISTORY_LENGTH=50

# 工具
SEARCH_BACKEND=tavily        # tavily | serpapi
TAVILY_API_KEY=
SERPAPI_API_KEY=

# 调试
DEBUG=false
LOG_LEVEL=INFO
```

> v0.1 **不引入 settings.yaml**。所有配置由 `Config.from_env()` 读取上述 env vars。`pyyaml` 也不在核心依赖里。

#### v0.3+ — 分层 `.env` + `settings.yaml`（D 阶段引入）

```yaml
# settings.yaml（v0.3+）—— 静态行为与组合配置
agent:
  max_steps: 5
  temperature: 0.0

tools:
  mcp_servers: []

observability:
  trace_enabled: true
  trace_export: console     # console | json | none
```

> 分层原则：`.env` 装 **凭证 / 端点**（运行环境差异），`settings.yaml` 装 **行为参数**（与运行环境无关）。Config 加载顺序：硬编码默认值 < `settings.yaml` < `.env` < 进程环境变量 < 显式 kwargs。

---
