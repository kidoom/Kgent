# DEV_SPEC: Kagent
> Version: 0.2 Draft — 2026-05-07
> 项目类型：Library/SDK（AI Agent 框架）
> 参考文档：Hello-Agents框架实现全景文档.md

> 命名约定：项目名使用 `Kagent`，Python 包名与 import 路径使用 `kagent`。

---

## 0. 速查索引（auto-coder 与新人开发者从这里开始）

> 本节是项目的"导航面板"。每个任务的**目标 / 文件 / 测试 / 依赖**一行可见，详细契约请跳转对应章节。
> **修改 spec 时，本节必须与 §5.2 目录结构、§6.3 任务卡保持一致**。

### 0.1 当前进度（截至 2026-05-07）

```
v0.1 Kagent Core MVP — 进行中
  阶段 A [████████] 8/8  ✅ 工程骨架 + LLM 可插拔 + 工具可插拔
  阶段 B [████████] 3/3  ✅ Agent 范式（B1 + B2 + B3 全部完成）
  阶段 C [████████] 4/4  ✅ 框架化加固（C1 + C2 + C3 + C8 全部完成）
v0.2 Kagent Core 增强 — ✅ 已完成
  阶段 C [████████] 4/4  ✅ C4+C5+C7+C9 全部完成
v0.3 Kagent Observability — ✅ 已完成
  阶段 D [████████] 8/8  ✅ Tracer + TraceExporter + Agent 埋点 + MCPTool + 容错 + 监控
v0.4 Kagent Memory — ✅ 已完成
  阶段 E [████████] 6/6  ✅ MemoryManager + Working/Episodic/Semantic + MemoryTool + ContextBuilder + NoteTool/TerminalTool
v0.5 Examples（F：旅行助手 / 深度研究 / 赛博小镇）
```

### 0.2 任务速查矩阵

> 列含义：**任务** / **目标一句话** / **主要文件** / **测试文件** / **前置依赖** / **MVP**
>
> ★ = v0.1 MVP 必做  ｜ ◇ = v0.2 (Core 增强)  ｜ △ = v0.3 (Observability)  ｜ ◯ = v0.4 (Memory) ｜ ▽ = v0.5 (Examples)

| 任务    | 目标                                                | 主要文件                                                                   | 测试文件                                                           | 依赖         | MVP |
| ----- | ------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------- | ---------- | --- |
| A1    | 目录骨架 + pyproject.toml + .env.example              | `pyproject.toml` `.env.example` `.gitignore` `kagent/**/__init__.py`   | （无）                                                            | —          | ★   |
| A2    | pytest 配置 + smoke test                            | `pyproject.toml` `tests/unit/test_smoke.py` `tests/fixtures/.env.test` | `test_smoke.py`                                                | A1         | ★   |
| A3    | Config 类 + .env 加载 + 校验                           | `kagent/core/config.py`                                                | `tests/unit/test_config.py`                                    | A1, A2     | ★   |
| A4    | LLMProvider ABC + Registry                        | `kagent/core/llm/{models,base}.py`                                     | `tests/unit/test_llm.py::TestLLMProvider*`                     | A1, A2     | ★   |
| A5    | AgentLLM 门面 + PROVIDER_CONFIG lazy-load           | `kagent/core/llm/factory.py`                                           | `tests/unit/test_llm.py::TestAgentLLM*`                        | A3, A4     | ★   |
| A6    | OpenAIProvider（client 复用）                         | `kagent/core/llm/providers.py`                                         | `tests/unit/test_llm.py::TestOpenAIProvider`                   | A4         | ★   |
| A7    | Tool ABC + ToolRegistry（含 enable/disable）         | `kagent/tools/{base,registry}.py`                                      | `tests/unit/test_tools.py::TestTool*`                          | A1, A2     | ★   |
| A8    | CalculatorTool（AST）+ SearchTool（Tavily/SerpApi）   | `kagent/tools/builtin/{calculator,search}.py`                          | `tests/unit/test_tools.py::TestCalculatorTool, TestSearchTool` | A7         | ★   |
| ——    | Stage A 集成                                        | —                                                                      | `tests/integration/test_llm_tool_wire.py`                      | A1-A8      | ★   |
| B1    | Agent ABC + Message                               | `kagent/core/{agent,message}.py`                                       | `tests/unit/test_{agent,message}.py`                           | A4, A5     | ★   |
| B2    | SimpleAgent                                       | `kagent/agents/simple_agent.py`                                        | `tests/unit/test_agent.py::TestSimpleAgent`                    | B1, A7     | ★   |
| B3    | ReActAgent                                        | `kagent/agents/react_agent.py`                                         | `tests/unit/test_agent.py::TestReActAgent`                     | B1, A7     | ★   |
| B4    | PlanAndSolveAgent                                 | `kagent/agents/plan_solve_agent.py`                                    | —                                                              | B1         | ◇   |
| B5    | ReflectionAgent                                   | `kagent/agents/reflection_agent.py`                                    | —                                                              | B1         | ◇   |
| B6    | FunctionCallAgent                                 | `kagent/agents/function_call_agent.py`                                 | —                                                              | B1, A7     | ◇   |
| ——    | Stage B 集成                                        | —                                                                      | `tests/integration/test_agent_with_tool.py`                    | B2-B3, A8  | ★   |
| C1    | 目录骨架验证 + import 全量可用                              | （仅检查）                                                                  | —                                                              | A1-B3      | ★   |
| C2    | 升级 KagentError 为双字段（user_message / debug_message） | `kagent/core/exceptions.py` + 所有 raise 处                               | `tests/unit/test_exceptions.py`                                | B3         | ★   |
| C3    | Agent 基类注入 Config + custom_prompt + run_id        | `kagent/core/agent.py`                                                 | `tests/unit/test_agent.py::TestAgentConfig, TestCustomPrompt`  | B1, A3     | ★   |
| C4    | 多 Provider（Ollama/VLLM/Zhipu）+ auto-detect        | `kagent/core/llm/{factory,providers}.py`                               | `tests/unit/test_llm.py::TestAutoDetect`                       | A5, A6     | ◇   |
| C5    | ToolRegistry 双注册 + 裸函数拔除                          | `kagent/tools/registry.py`                                             | `tests/unit/test_tools.py::TestRegistryFramework`              | A7         | ◇   |
| C6    | SimpleAgent 框架化                                   | `kagent/agents/simple_agent.py`                                        | `tests/unit/test_agent.py::TestSimpleAgent`（扩展）                | B2, C2, C3 | ◇   |
| C7    | ReActAgent 框架化（含 custom_prompt 模板）                | `kagent/agents/react_agent.py`                                         | `tests/unit/test_agent.py::TestReActAgent`（扩展）                 | B3, C2, C3 | ◇   |
| C8    | pip install -e . 验证 + 最小 README                   | `pyproject.toml` `README.md`                                           | `tests/integration/test_{framework_import,pip_install}.py`     | C1-C3      | ★   |
| C9    | FunctionCallAgent 框架化 + 并行工具调用                    | `kagent/agents/function_call_agent.py`                                 | —                                                              | B6, C2, C5 | ◇   |
| D1    | Span + Tracer（contextvars 并发隔离）                   | `kagent/core/tracing/{models,tracer}.py`                               | `tests/unit/test_tracing.py::TestTracer`                       | C2         | △   |
| D2    | TraceExporter（dict/json/tree）                     | `kagent/core/tracing/exporter.py`                                      | `tests/unit/test_tracing.py::TestExporter`                     | D1         | △   |
| D3    | Agent 埋点（AGENT_RUN/STEP/LLM_CALL/TOOL_CALL）       | `kagent/agents/{simple,react}_agent.py`                                | `tests/integration/test_agent_with_tracing.py`                 | D1, B3     | △   |
| D4    | MCPTool（子进程 + tools/list / tools/call）            | `kagent/tools/mcp_tool.py`                                             | `tests/integration/test_mcp.py`                                | A7         | △   |
| D5    | MCP Server 模板                                     | `kagent/tools/mcp_server_template.py`                                  | （由 D4 集成测试覆盖）                                                  | D4         | △   |
| D6    | ToolRegistry.register_mcp()                       | `kagent/tools/registry.py`                                             | `tests/integration/test_mcp.py`                                | D4, A7     | △   |
| D7    | 容错增量（LLM 重试 / 锁 / 缓存 / MCP 重连）                    | 多文件，见 §6.3 D7                                                          | `tests/unit/test_fault_tolerance.py`                           | C2, D1-D6  | △   |
| D8    | 监控（Token 统计 + run_id + 结构化日志）                     | `kagent/core/{tracing,llm/factory,agent}.py`                           | `tests/unit/test_tracing.py::test_token_stats`                 | D1, D3, C3 | △   |
| E1-E5 | Memory + ContextBuilder + NoteTool/TerminalTool   | `kagent/memory/*` `kagent/context/*`                                   | —                                                              | D 阶段       | ◯   |
| F1-F3 | 旅行助手 / 深度研究 / 赛博小镇                                | `projects/*/main.py`                                                   | （手动）                                                           | E 阶段       | ▽   |

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

v0.1 所有行为由 `.env` 控制：LLM Provider 选择、Provider 凭证、模型 ID、工具开关、日志级别等。v0.3+ 再引入 `settings.yaml` 承载静态行为与组合配置。

#### 3）链路追踪是基础设施（"Agent 出问题不靠 print 大海捞针"）

每次 Agent 运行的完整执行树、每步耗时、LLM 输入/输出、工具参数/结果全部结构化记录，支持终端树形图和 JSON 双格式导出。

### 1.3 目标受众

| 受众 | 获得什么 | 使用方式 |
|------|---------|---------|
| AI 应用开发者 | 快速构建 Agent 应用 | `pip install kagent` → `from kagent import ...` |
| Agent 学习者 | 框架源码可读，渐进式学习 | 按阶段构建，每阶段可独立运行 |
| 工具开发者 | 写一个 Tool/Provider 即可接入 | 实现 `Tool.run()` 或 `LLMProvider.chat()` |

### 1.4 范围边界

**v0.1 MVP 必须完成（= Kagent Core 子项目）：**
- pip 可安装的 `kagent` 包与最小目录骨架
- LLM Provider 抽象、注册中心、OpenAI 兼容 Provider、配置驱动选择（含 PROVIDER_CONFIG 自动 lazy-load）
- Tool 抽象、ToolRegistry、CalculatorTool、SearchTool（真实外部搜索测试 `external` 标记，CI 跳过）
- SimpleAgent / ReActAgent 两种基础 Agent
- Config 类 + KagentError 异常体系（双字段 user_message / debug_message）
- `pip install -e .` 后 `from kagent import SimpleAgent, ReActAgent, AgentLLM, Config` 可用
- 单元测试 ≥ 55 用例 + Mock 集成测试 ≥ 8 用例 + 最小 README 示例

**MVP 硬截止线：A1-A8 + B1-B3 + C1-C3 + C8。** C4/C5/C6/C7/C9（多 Provider 扩展、Agent 进一步加固）以及 D/E/F 阶段全部属于 v0.2+。

**显式不在 v0.1 范围内：**
- ❌ Tracer / Span / TraceExporter — v0.3 Observability 子项目（D 阶段）
- ❌ MCPTool / MCP 容错与重连 — v0.3（D 阶段）
- ❌ PlanAndSolveAgent / ReflectionAgent / FunctionCallAgent — v0.2 Core 增强（B4-B6 + C9）
- ❌ Memory 系统 / ContextBuilder — v0.4 Memory 子项目（E 阶段）
- ❌ settings.yaml 分层配置 — v0.3+ 引入（v0.1 仅 .env，见 §5.4）
- ❌ 实战项目（旅行助手 / 深度研究 / 赛博小镇）— v0.5 Examples 子项目（F 阶段）

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
- LLM 调用层（可插拔 Provider 注册制 + PROVIDER_CONFIG 自动 lazy-load，内置 OpenAI，其余 Provider 为 v0.2+）
- 2 种 Agent 范式（SimpleAgent / ReActAgent）
- 可插拔工具系统（本地 Tool + 裸函数注册 + 工具 lifecycle: enable/disable）
- Config 类 + KagentError 异常体系（双字段）+ pip install -e .
- 内置工具：CalculatorTool（AST 安全求值）+ SearchTool（SerpApi/Tavily 二选一）

**v0.2+（后续版本，不在本 spec 的实施范围内）：**
- 5 种 Agent 范式补齐（PlanAndSolveAgent / ReflectionAgent / FunctionCallAgent）
- 多 Provider 扩展（ModelScope/Zhipu/Ollama/VLLM + auto-detect）
- MCP 远程服务 + 容错重试 + 监控
- MemoryTool（Working / Episodic / Semantic 三层记忆）
- ContextBuilder（GSSC 上下文流水线）
- 3 个实战参考项目（旅行助手 / 深度研究 / 赛博小镇）

**v0.1 后续路线：**
- **v0.2 — Kagent Core 增强**（C4-C7 + C9）：多 Provider（ModelScope/Zhipu/Ollama/VLLM + auto-detect）、PlanAndSolveAgent / ReflectionAgent / FunctionCallAgent 三种范式补齐
- **v0.3 — Kagent Observability**（D 阶段全部）：Tracer / TraceExporter / Agent 埋点、MCPTool + MCP Server 模板、容错重试与缓存、监控（Token 统计 + run_id + 结构化日志）
- **v0.4 — Kagent Memory**（E 阶段全部）：BaseMemory / MemoryManager / Working / Episodic / Semantic、MemoryTool、ContextBuilder（GSSC）、NoteTool / TerminalTool
- **v0.5 — Examples**（F 阶段全部）：旅行助手 / 深度研究 / 赛博小镇骨架，作为框架能力验收样例，不阻塞核心包发布

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
| B4 | PlanAndSolveAgent | [x] | 2026-05-08 | Plan→Execute 两阶段；ast.literal_eval 解析计划；AgentError 处理 |
| B5 | ReflectionAgent | [x] | 2026-05-08 | Execute→Reflect→Refine 迭代；"无需改进"提前终止；max_steps 硬上限 |
| B6 | FunctionCallAgent | [x] | 2026-05-09 | native function calling；9 测试覆盖 tool_call/error/nonexistent/max_steps |

#### 阶段 C — 框架化加固

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| C1 | 框架目录骨架 | [x] | 2026-05-07 | 补充 kagent/__init__.py 导出 SimpleAgent/ReActAgent，全量 import 验证 |
| C2 | Config 类 + 异常体系 | [x] | 2026-05-07 | KagentError 升级双字段 user_message/debug_message，向后兼容 |
| C3 | Agent 基类框架化 | [x] | 2026-05-07 | 注入 custom_prompt 模板变量 + run_id + _format_prompt |
| C4 | AgentLLM 框架化（多 Provider） | [x] | 2026-05-08 | ZhipuProvider + ModelScopeProvider + auto-detect；PROVIDER_CONFIG 扩充至 5 个 provider |
| C5 | ToolRegistry 框架化（双注册 + 裸函数拔除） | [x] | 2026-05-08 | v0.1 已实现双注册；补充 TestRegistryFramework 验收测试 |
| C6 | SimpleAgent 框架化 | [x] | 2026-05-09 | v0.1 C2/C3 已注入 Config/custom_prompt/run_id；与 B2 功能一致 |
| C7 | ReActAgent 框架化 | [x] | 2026-05-09 | v0.1 C2/C3 已注入 Config/custom_prompt/run_id；与 B3 功能一致 |
| C8 | pip install 验证 | [x] | 2026-05-07 | README + framework import tests + pip install tests (external) |
| C9 | FunctionCallAgent 框架化 | [x] | 2026-05-09 | B6 已内置 Config/custom_prompt/run_id/ToolRegistry；含并行 tool_calls 支持 |

#### 阶段 D — MCP 外部网关 + 链路追踪 + 容错 + 监控

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| D1 | Span + Tracer 数据模型 | [x] | 2026-05-09 | Span/Tracer/contextvars 并发隔离；16 单元测试 |
| D2 | TraceExporter | [x] | 2026-05-09 | dict/json/tree 三种导出格式；含 token 汇总 |
| D3 | Agent 埋点集成 | [x] | 2026-05-09 | SimpleAgent + ReActAgent 埋入 trace/step/llm/tool spans |
| D4 | MCPTool | [x] | 2026-05-09 | 子进程 + JSON-RPC 2.0 + tools/list + tools/call + 自动重连 |
| D5 | MCP Server 模板 | [x] | 2026-05-09 | mcp_server_template.py：search_docs + list_sources |
| D6 | MCP + ToolRegistry 集成 | [x] | 2026-05-09 | register_mcp() 自动发现 + 批量注册；ToolRegistry 加锁 |
| D7 | 容错机制 | [x] | 2026-05-09 | LLM 指数退避重试 + SearchTool 5s 缓存 + MCP 重连 + Registry 加锁 |
| D8 | 监控（日志 + trace_id + Token） | [x] | 2026-05-09 | AgentLLM 自动注入 token_usage 到 Tracer span；run_id 贯穿 trace |

#### 阶段 E — 记忆系统 + 上下文工程

| 编号 | 任务 | 状态 | 完成日期 | 备注 |
|------|------|------|---------|------|
| E1 | Memory 基类 + MemoryManager | [x] | 2026-05-09 | BaseMemory ABC + MemoryItem + MemoryManager 多后端编排 |
| E2 | WorkingMemory + EpisodicMemory | [x] | 2026-05-09 | TTL+容量 LRU 淘汰 / 时间序列+时间范围检索 |
| E2.5 | SemanticMemory | [x] | 2026-05-09 | 可插拔 embedding_fn + 余弦相似度 + 子串回退 |
| E3 | MemoryTool | [x] | 2026-05-09 | remember/recall 操作封装为 Tool |
| E4 | ContextBuilder | [x] | 2026-05-09 | GSSC 流水线 (Gather→Select→Structure→Compress) |
| E5 | NoteTool + TerminalTool | [x] | 2026-05-09 | 笔记 CRUD + 只读文件系统 (路径越界防护) |

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


## 7. Axioms（内嵌原则）

1. **Spec before implementation** — 接口 + 契约 + 验收标准先于代码定义
2. **One hour, one verifiable increment** — 每个任务 ~1h，有可测试的输出
3. **Test-first, always** — 先写测试方法，再写代码
4. **Interfaces before implementations** — 抽象基类 + 工厂先于具体实现
5. **Configuration drives behavior** — 单一配置源，切换零代码改动
6. **Fail fast, degrade gracefully** — 启动时校验，运行时降级；工具失败返回用户可读错误，不中断 Agent 循环
7. **Observability is not optional** — 每次 run() 生成 trace_id + 结构日志 + Token 用量统计
8. **SPEC is a living document** — 每完成一个任务更新进度表
