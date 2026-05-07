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
