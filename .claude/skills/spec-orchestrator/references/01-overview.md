## 1. 项目概述

### 1.1 背景

HelloAgents 是一个从零构建的 AI-Native 智能体框架。项目解决的核心问题是：当前主流 Agent 框架（LangChain、AutoGen 等）抽象过重、概念过多，初学者难以穿透框架表象理解智能体的本质。本框架基于 OpenAI 兼容 API，从最简核心出发，逐步扩展到记忆、上下文工程、通信协议、多智能体协作，最终支撑真实应用（旅行助手、深度研究、赛博小镇）。

### 1.2 设计理念

> **核心定位：教是最好的学——穿透框架，直抵本质**

本框架不是又一个生产级 Agent SDK，而是一个教学驱动的、从零到一的智能体构建指南。每个模块的设计都服务于一个教学目标：让学习者真正理解"智能体是怎么工作的"。

#### 1）最小核心，渐进扩展（Minimal Core, Progressive Expansion）

框架从 5 个核心抽象（Agent、LLM、Message、Tool、Config）出发，每章新增一个可理解的增量。不做过度设计——先让 ReAct 跑通，再加 Plan-and-Solve，再加 Reflection，再加 Memory。每一章的代码都是上一章的自然演进，而非推倒重来。

#### 2）万物皆工具（Everything is a Tool）

Memory、RAG、MCP、A2A、ANP——所有能力都通过统一的 `Tool` 接口暴露给 Agent。这避免了 LangChain 式的"每种能力一套独立抽象"的复杂性。Agent 不需要知道它调用的是本地函数、远程 MCP 服务还是另一个 Agent——它只知道"我有工具，我调用它"。

#### 3）AI-Native，非流程驱动（AI-Native, Not Workflow-Driven）

区别于 Dify、Coze、n8n 等低代码平台（本质是流程驱动的软件开发，LLM 作为数据处理后端），本框架构建的是真正以 LLM 推理为核心驱动力的智能体。Agent 的行为由 LLM 的 Thought 决定，而非预定义的工作流。

### 1.3 目标受众

| 受众 | 他们获得什么 | 他们如何使用 |
|------|------------|------------|
| AI 开发初学者 | 从零理解 Agent 的核心原理 | 逐章学习，每章动手实现 |
| 求职面试者 | 可写进简历的完整项目 + 面试题答案 | 重点掌握框架设计、经典范式、评估体系 |
| 框架使用者 | `pip install hello-agents` 即可使用 | 导入框架，注册工具，运行 Agent |
| 框架扩展者 | 清晰的接口定义和扩展点 | 实现新 Agent 范式、新 Tool、新 Memory 类型 |

### 1.4 范围边界

**范围内：**
- 5 种 Agent 范式（Simple、ReAct、Plan-and-Solve、Reflection、FunctionCall）
- 可插拔 LLM 多 Provider 支持（OpenAI/Azure/Ollama/DeepSeek/ModelScope）
- 统一 Tool 系统（函数注册 + Tool 子类 + ToolChain + 异步执行）
- 4 层记忆系统（Working/Episodic/Semantic/Perceptual）
- 上下文工程（GSSC Pipeline）
- 通信协议集成（MCP/A2A/ANP 作为 Tool）
- 评估框架（BFCL/GAIA/LLM Judge）
- 3 个综合应用案例

**明确排除：**
- 生产级分布式部署 — 本框架定位为教学和原型验证
- GUI/Web 前端 — 框架本身是纯 Python 库，应用案例的前端由案例自行提供
- 模型训练基础设施 — Agentic RL（第十一章）是独立模块，不纳入框架核心

---