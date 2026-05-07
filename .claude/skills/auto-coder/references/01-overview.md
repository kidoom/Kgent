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
