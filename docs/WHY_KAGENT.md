# WHY KAGENT — 面试话术脚本

> 这不是给 CC 看的执行文档。这是你面试时被问"为什么不直接用 LangChain/为什么做这个项目"时的标准答案。
> 每一句话都必须是你实际做过的——没读过的源码别说读过了，没对比过的别说对比过了。

---

## 30 秒电梯演讲

> "Kagent 是一个带内置可观测性的 ReAct Agent 引擎 SDK。它不是 LangChain 的替代品——它是我理解 Agent 底层原理的工程证明。我重点解决了三个问题：LLM 与 Provider 的解耦、工具系统的统一注册、以及从第一天就内建在 Agent.run() 里的链路追踪。我在做的过程中读了 LangChain 的 AgentExecutor、Tool、Callback 三个核心模块，还有 Hermes Agent 的记忆分层设计。我的设计取舍都建立在对这些系统的理解之上。"

---

## 赛道格局（2026 年 5 月）

| 产品 | 定位 | Star | 核心差异 |
|------|------|------|---------|
| **Claude Code** | IDE 编码副驾驶 | ~140K | Skill 生态 + MCP 协议，把编码场景打透了 |
| **Hermes Agent** | 自进化个人 Agent | 57K+ | MIT 开源、18+ 模型提供商、分层记忆、自学习闭环 |
| **OpenClaw** | 多渠道 Agent 平台 | 247K | 生态最大，但太重 |
| **LangChain** | Agent 框架 SDK | 100K+ | 覆盖面广但过度抽象、追踪靠 callback 插件 |
| **Kagent（你）** | 可嵌入 Agent 引擎 SDK | - | LLM 解耦、追踪内建、工具统一注册 |

**关键认知**：Claude Code 和 Hermes 是产品，Kagent 是 SDK/库——品类不同，不直接竞争。

---

## 你的三个设计取舍（面试深聊素材）

### 取舍 1：LLM Provider 一行切换 vs LangChain 的硬编码

**LangChain 怎么做的**：ChatOpenAI、ChatAnthropic、ChatOllama 等各自独立的类，切换模型 = 改 import + 改初始化代码。

**你怎么做的**：`LLMProvider` 抽象基类 → `LLMProviderRegistry` 注册中心 → `AgentLLM` 门面从 `.env` 读取 `LLM_PROVIDER` 名称 → 查 `PROVIDER_CONFIG` 字典 → 自动实例化对应 Provider。

```python
# 切换 LLM：只改 .env，代码零改动
# LLM_PROVIDER=openai  →  LLM_PROVIDER=ollama
agent = ReActAgent(llm=AgentLLM(), tools=[...])  # 这行不变
```

**面试说法**："LangChain 的 Chat Model 体系功能强但和 Provider 耦合——每加一个服务商要改实例化代码。我用了注册制 + 配置字典的方式，Provider 的发现、凭证读取、实例化全部由框架处理，用户只改一行 .env。这不是说我的方案更好，而是我的定位不同——Kagent 追求的是零学习成本的 Provider 切换。"

### 取舍 2：追踪内建 vs LangChain 的 Callback 插件

**LangChain 怎么做的**：`BaseCallbackHandler` 继承 → `on_llm_start()` / `on_llm_end()` / `on_tool_start()` 等钩子 → 通过 `callbacks=[...]` 参数注入 Agent。

**你怎么做的**：`Tracer` 单例 + `Span` 树形数据结构 + Context Manager 语法糖（`with tracer.span() as s:`）→ Agent.run() 内部自动埋点 → `TraceExporter` 导出为终端树形图 / JSON / dict。

**核心差异**：LangChain 把追踪当"用户可选的 callback 插件"——默认不启用。Kagent 把追踪当基础设施——每次 run() 自动生成完整 Span 树。

**面试说法**："我做 ReActAgent 时发现执行链路很长——LLM 调用 → 解析 Thought/Action → 工具执行 → 再调 LLM——出错时靠 print 完全定位不了问题。LangChain 的 callback 体系能解决，但它需要额外配置才能看到调用链。我的设计是：追踪不是可选项，是每次 run() 的默认行为。`trace_enabled=False` 也只是不打印输出，数据还在。Context Manager 语法糖让埋点代码和业务逻辑完全解耦。"

### 取舍 3：三种工具注册合一 vs 业界常见的单一注册方式

**业界常见做法**：LangChain 用 `@tool` 装饰器，LlamaIndex 用 `FunctionTool` 包装。工具来源不同（本地函数 / 远程 API / RAG 项目）就需要不同的接入代码。

**你怎么做的**：`ToolRegistry` 提供三种统一的注册入口——`register_tool(Tool对象)` / `register_function(裸函数)` / `register_mcp(MCP远程服务)`。三种来源共享同一个 `execute_tool(name, arguments) -> ToolResult` 通道。Agent 不关心工具从哪来。

**面试说法**："MCP 协议正在成为 Agent 工具接入的事实标准——Claude Code 的 MCP 生态证明了这一点。我在设计 Kagent 的工具系统时，把 MCP 定位为'统一的外部能力网关'而不是'三种协议之一'。这样用户的 RAG 项目、GitHub API、数据库——不管什么外部能力，都通过 MCP Server 接入，ToolRegistry 对 Agent 呈现为统一的工具列表。"

---

## Hermes Agent 的启示

Hermes 的分层记忆（MEMORY.md + USER.md + 主动压缩）是其核心卖点。我读了它的设计后做了不同取舍：

- **Hermes 用文件系统做记忆**：简单、持久、可直接编辑。但并发读写有风险，且不适合高频检索。
- **Kagent 用 Python 对象 + 可选向量存储**：WorkingMemory 是 Python dict（当前对话）、EpisodicMemory 是时间序列列表、SemanticMemory 支持可插拔的 embedding 函数。更适合嵌入到后端服务中。

**面试说法**："Hermes 用 markdown 文件做分层记忆，适合单用户 Agent。Kagent 定位是 SDK，要被嵌入到多用户的后端服务里——Python 对象天然线程安全，也可以替换后端存储（SQLite → Qdrant）。这是一个情境化的取舍，不是谁好谁坏。"

---

## 面试常见追问 + 应答

### Q: "你的框架和 LangChain 有什么区别？"
**A**: 见取舍 1/2/3。结尾："我的目的不是替代 LangChain——它是生产级框架，有 100K+ star 和全职团队维护。我做 Kagent 是为了理解 Agent 的底层原理，并且在一个问题上做深——Agent 的可观测性。"

### Q: "你为什么不用 LangChain 而要自己写一个？"
**A**: "我用过 LangChain。它的 AgentExecutor 用了 4 层间接调用来编排 Thought→Action→Observation 循环，学习曲线陡。我想从零实现一遍，这样以后用 LangChain 也能理解它的设计决策。自己做一遍 = 最好的学习。"

### Q: "你的框架在生产环境能用吗？"
**A**: "v0.1 是理解原理的工程证明，不是生产框架。但我做的三个设计是生产级的：Provider 注册制、Span Tree 追踪、工具统一注册。后续如果要生产化，每个模块都有明确的扩展点。"

### Q: "你关注过 Claude Code / Hermes Agent 吗？"
**A**: 见赛道格局表 + Hermes 启示。核心观点："它们是产品，Kagent 是 SDK——品类不同。但它们的成功验证了两个趋势：MCP 成为工具标准、可观测性是 Agent 落地的刚需。这两个趋势直接影响了 Kagent 的设计。"
