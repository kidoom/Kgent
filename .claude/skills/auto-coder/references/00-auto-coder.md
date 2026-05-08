## 0. 速查索引（auto-coder 与新人开发者从这里开始）

> 本节是项目的"导航面板"。每个任务的**目标 / 文件 / 测试 / 依赖**一行可见，详细契约请跳转对应章节。
> **修改 spec 时，本节必须与 §5.2 目录结构、§6.3 任务卡保持一致**。

### 0.1 当前进度（截至 2026-05-07）

```
v0.1 Kagent Core MVP — 进行中
  阶段 A [████████] 8/8  ✅ 工程骨架 + LLM 可插拔 + 工具可插拔
  阶段 B [████████] 3/3  ✅ Agent 范式（B1 + B2 + B3 全部完成）
  阶段 C [████████] 4/4  ✅ 框架化加固（C1 + C2 + C3 + C8 全部完成）
v0.2+ — 未启动
  v0.2 Kagent Core 增强（C4-C7 + C9：多 Provider / 5 范式齐备）
  v0.3 Kagent Observability（D：Tracer + MCP + 容错 + 监控）
  v0.4 Kagent Memory（E：MemoryManager / ContextBuilder / Note&Terminal）
  v0.5 Examples（F：旅行助手 / 深度研究 / 赛博小镇）
```

### 0.2 任务速查矩阵

> 列含义：**任务** / **目标一句话** / **主要文件** / **测试文件** / **前置依赖** / **MVP**
>
> ★ = v0.1 MVP 必做  ｜ ◇ = v0.2 (Core 增强)  ｜ △ = v0.3 (Observability)  ｜ ◯ = v0.4 (Memory) ｜ ▽ = v0.5 (Examples)

| 任务 | 目标 | 主要文件 | 测试文件 | 依赖 | MVP |
|------|------|---------|---------|------|-----|
| A1 | 目录骨架 + pyproject.toml + .env.example | `pyproject.toml` `.env.example` `.gitignore` `kagent/**/__init__.py` | （无） | — | ★ |
| A2 | pytest 配置 + smoke test | `pyproject.toml` `tests/unit/test_smoke.py` `tests/fixtures/.env.test` | `test_smoke.py` | A1 | ★ |
| A3 | Config 类 + .env 加载 + 校验 | `kagent/core/config.py` | `tests/unit/test_config.py` | A1, A2 | ★ |
| A4 | LLMProvider ABC + Registry | `kagent/core/llm/{models,base}.py` | `tests/unit/test_llm.py::TestLLMProvider*` | A1, A2 | ★ |
| A5 | AgentLLM 门面 + PROVIDER_CONFIG lazy-load | `kagent/core/llm/factory.py` | `tests/unit/test_llm.py::TestAgentLLM*` | A3, A4 | ★ |
| A6 | OpenAIProvider（client 复用） | `kagent/core/llm/providers.py` | `tests/unit/test_llm.py::TestOpenAIProvider` | A4 | ★ |
| A7 | Tool ABC + ToolRegistry（含 enable/disable） | `kagent/tools/{base,registry}.py` | `tests/unit/test_tools.py::TestTool*` | A1, A2 | ★ |
| A8 | CalculatorTool（AST）+ SearchTool（Tavily/SerpApi） | `kagent/tools/builtin/{calculator,search}.py` | `tests/unit/test_tools.py::TestCalculatorTool, TestSearchTool` | A7 | ★ |
| —— | Stage A 集成 | — | `tests/integration/test_llm_tool_wire.py` | A1-A8 | ★ |
| B1 | Agent ABC + Message | `kagent/core/{agent,message}.py` | `tests/unit/test_{agent,message}.py` | A4, A5 | ★ |
| B2 | SimpleAgent | `kagent/agents/simple_agent.py` | `tests/unit/test_agent.py::TestSimpleAgent` | B1, A7 | ★ |
| B3 | ReActAgent | `kagent/agents/react_agent.py` | `tests/unit/test_agent.py::TestReActAgent` | B1, A7 | ★ |
| B4 | PlanAndSolveAgent | `kagent/agents/plan_solve_agent.py` | — | B1 | ◇ |
| B5 | ReflectionAgent | `kagent/agents/reflection_agent.py` | — | B1 | ◇ |
| B6 | FunctionCallAgent | `kagent/agents/function_call_agent.py` | — | B1, A7 | ◇ |
| —— | Stage B 集成 | — | `tests/integration/test_agent_with_tool.py` | B2-B3, A8 | ★ |
| C1 | 目录骨架验证 + import 全量可用 | （仅检查） | — | A1-B3 | ★ |
| C2 | 升级 KagentError 为双字段（user_message / debug_message） | `kagent/core/exceptions.py` + 所有 raise 处 | `tests/unit/test_exceptions.py` | B3 | ★ |
| C3 | Agent 基类注入 Config + custom_prompt + run_id | `kagent/core/agent.py` | `tests/unit/test_agent.py::TestAgentConfig, TestCustomPrompt` | B1, A3 | ★ |
| C4 | 多 Provider（Ollama/VLLM/Zhipu）+ auto-detect | `kagent/core/llm/{factory,providers}.py` | `tests/unit/test_llm.py::TestAutoDetect` | A5, A6 | ◇ |
| C5 | ToolRegistry 双注册 + 裸函数拔除 | `kagent/tools/registry.py` | `tests/unit/test_tools.py::TestRegistryFramework` | A7 | ◇ |
| C6 | SimpleAgent 框架化 | `kagent/agents/simple_agent.py` | `tests/unit/test_agent.py::TestSimpleAgent`（扩展） | B2, C2, C3 | ◇ |
| C7 | ReActAgent 框架化（含 custom_prompt 模板） | `kagent/agents/react_agent.py` | `tests/unit/test_agent.py::TestReActAgent`（扩展） | B3, C2, C3 | ◇ |
| C8 | pip install -e . 验证 + 最小 README | `pyproject.toml` `README.md` | `tests/integration/test_{framework_import,pip_install}.py` | C1-C3 | ★ |
| C9 | FunctionCallAgent 框架化 + 并行工具调用 | `kagent/agents/function_call_agent.py` | — | B6, C2, C5 | ◇ |
| D1 | Span + Tracer（contextvars 并发隔离） | `kagent/core/tracing/{models,tracer}.py` | `tests/unit/test_tracing.py::TestTracer` | C2 | △ |
| D2 | TraceExporter（dict/json/tree） | `kagent/core/tracing/exporter.py` | `tests/unit/test_tracing.py::TestExporter` | D1 | △ |
| D3 | Agent 埋点（AGENT_RUN/STEP/LLM_CALL/TOOL_CALL） | `kagent/agents/{simple,react}_agent.py` | `tests/integration/test_agent_with_tracing.py` | D1, B3 | △ |
| D4 | MCPTool（子进程 + tools/list / tools/call） | `kagent/tools/mcp_tool.py` | `tests/integration/test_mcp.py` | A7 | △ |
| D5 | MCP Server 模板 | `kagent/tools/mcp_server_template.py` | （由 D4 集成测试覆盖） | D4 | △ |
| D6 | ToolRegistry.register_mcp() | `kagent/tools/registry.py` | `tests/integration/test_mcp.py` | D4, A7 | △ |
| D7 | 容错增量（LLM 重试 / 锁 / 缓存 / MCP 重连） | 多文件，见 §6.3 D7 | `tests/unit/test_fault_tolerance.py` | C2, D1-D6 | △ |
| D8 | 监控（Token 统计 + run_id + 结构化日志） | `kagent/core/{tracing,llm/factory,agent}.py` | `tests/unit/test_tracing.py::test_token_stats` | D1, D3, C3 | △ |
| E1-E5 | Memory + ContextBuilder + NoteTool/TerminalTool | `kagent/memory/*` `kagent/context/*` | — | D 阶段 | ◯ |
| F1-F3 | 旅行助手 / 深度研究 / 赛博小镇 | `projects/*/main.py` | （手动） | E 阶段 | ▽ |

### 0.3 关键设计常量

| 常量 | 值 | 来源 |
|------|-----|------|
| Python 最低版本 | `>=3.10` | §3.0 pyproject.toml |
| LLM 默认 provider | `openai` | `Config.default_provider` |
| LLM 默认 model | `gpt-4o` | `Config.default_model` |
| 默认 max_steps | 5 | `Config.max_steps` |
| 默认 max_history_length | 50 | `Config.max_history_length` |
| 默认 search backend | `tavily` | `SearchTool` + `.env.example` |
| LLM 重试退避 | 1s → 2s → 4s, 3 次 | §3.7 L3（v0.3 起，D7 落地） |
| Search 幂等窗口 | 5s | §3.7 I1（v0.3 起，D7 落地） |
| MCP 重连次数 | 3（30s 超时） | §3.7（v0.3 起，D7 落地） |

### 0.4 三大设计哲学（出处 §1.2）

1. **可插拔注册制** — 新增 = 写一个类 + 在 `PROVIDER_CONFIG` / `ToolRegistry` 加一行
2. **配置驱动** — 切换 LLM / 模型 / 工具开关 = 改 `.env` 一行，代码零改动
3. **链路追踪是基础设施**（v0.3 起强制）— 每次 `run()` 一棵 Span 树 + Token 统计 + run_id

### 0.5 八条 Axioms（出处 §7）

1. Spec before implementation｜2. One hour, one verifiable increment｜3. Test-first, always
4. Interfaces before implementations｜5. Configuration drives behavior｜6. Fail fast, degrade gracefully
7. Observability is not optional（v0.3 起）｜8. SPEC is a living document

### 0.6 给 auto-coder 的检索路径

> 当 auto-coder（或新人）准备开始一个任务，按下面四步走：
>
> 1. **§0.2 速查矩阵** 找到任务行 → 拿到「主要文件 / 测试文件 / 依赖」
> 2. **§5.2 目录结构** 确认文件路径与标记（★ 必做 / △/◇/◯/▽ 后续版本）
> 3. **§6.3 任务卡** 读完整契约（目标 / 类函数签名 / 验收 / 测试命令）
> 4. **§3.7 运行时契约** 查该任务涉及的运行时约束（异常处理 / 重试 / 并发 / 安全）
>
> 写代码前先写测试（§4.1 TDD），文件必须落到 §5.2 指定路径，不要自创目录。

---
