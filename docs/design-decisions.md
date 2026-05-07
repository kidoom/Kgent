# Kagent 设计决策记录

> 这不是 CC 执行文档。这是你面试时被追问"为什么这样做"时的技术论证素材。每个决策都记录了备选方案和选择理由。

---

## 决策 1：Context Manager vs Callback 继承做追踪埋点

**背景**：Agent 的每次 LLM 调用、工具执行都需要记录到 Span 树中。如何让埋点代码侵入性最小？

| 维度 | Context Manager (`with tracer.span() as s:`) | Callback 继承 (`class X(BaseCallbackHandler)`) |
|------|------|------|
| 代码侵入性 | 低——在 Agent.run() 内部直接包裹，一行 with | 中——需要定义回调类 + 传参 |
| 默认行为 | 开箱即用，不需要用户配置 | 默认不启用，需要用户主动注入 |
| 异常处理 | `__exit__` 自动捕获异常 + 标记 status=ERROR | 需要 `on_llm_error` 钩子，不触发则异常丢失 |
| 学习成本 | 理解 `__enter__`/`__exit__` 即可 | 需要理解 9 个钩子方法（on_llm_start, on_llm_end, on_llm_error, on_tool_start...） |
| LangChain 采用 | ❌ | ✅ |

**选择：Context Manager。** 
- 理由：Agent 执行天然是嵌套调用（run→step→llm→tool），Context Manager 的嵌套 `with` 语句直接映射执行树。
- 代价：需要 `Tracer` 维护当前活跃 Span 的栈（用 `contextvars`），增加 ~20 行实现代码。

---

## 决策 2：`contextvars` vs `threading.local` 做并发隔离

**背景**：`Tracer` 是单例，多个 Agent 并发运行时，必须保证每个 Agent 的 Span 数据互相隔离。

| 维度 | `contextvars` | `threading.local` |
|------|-------------|------------------|
| threading 支持 | ✅ | ✅ |
| asyncio 支持 | ✅（原生） | ❌（async 协程共享线程，会串） |
| 实现复杂度 | 中等（需要理解 Python context 模型） | 低 |
| 后续扩展 | 天然支持 async Agent | 需要迁移 |
| Python 版本 | 3.7+ | 全版本 |

**选择：`contextvars`。**
- 理由：v0.1 先做同步 Agent，但 `contextvars` 天然支持 async，为后续 async Agent 免迁移。
- 代价：实现比 `threading.local` 多 5 行（`ContextVar` 声明 + `Token` 管理），但换来了零迁移成本。

---

## 决策 3：树形 Span vs 扁平 Span + 排序做链路追踪

**背景**：每次 Agent 执行产生多个 Span（AGENT_RUN 根节点 → AGENT_STEP 中间节点 → LLM_CALL/TOOL_CALL 叶子节点）。如何组织这些 Span？

| 维度 | 树形（parent-children 嵌套） | 扁平列表（按时间排序） |
|------|------|------|
| 数据模型直觉 | ✅ 执行树 = Span 树，一一对应 | ❌ 需要额外排序还原执行顺序 |
| 序列化 | `children` 递归 → 天然 JSON 树 | 需要 `parent_id` 字段 + 重建算法 |
| 终端展示 | ✅ `├──` `└──` 树形输出直接可用 | ❌ 需要额外构建树才能展示 |
| 内存占用 | 每个 Span 持有 children 列表引用 | 每个 Span 只存 parent_id 字符串 |
| 遍历 | 深度优先遍历即执行顺序 | 需要拓扑排序 |

**选择：树形。**
- 理由：Agent 的执行过程天然是嵌套调用树，数据结构应该直接映射问题域。内存多占一点（children 列表引用 ≈ 8 bytes/child）可以忽略。
- 代价：构建树时需要维护 `parent_id → Span` 索引（一个 dict），约 10 行额外代码。

---

## 决策 4：ToolRegistry 三种注册方式合一 vs 分离

**背景**：工具有三种来源——本地 Tool 对象（Calculator）、裸 Python 函数（lambda/普通函数）、MCP 远程服务（RAG 项目）。

| 维度 | 三种合一（共享 execute_tool 通道） | 三种分离（各自独立的 registry） |
|------|------|------|
| Agent 调用 | `execute_tool(name, args)` 一个方法 | 需要 if/else 判断工具类型后调不同方法 |
| Agent Prompt | `get_tools_description()` 统一返回 | 需要分别获取 + 拼接 |
| 扩展性 | 新增来源 = 新增 `register_X` + 内部适配 | 新增来源 = 新增 Registry + Agent 层适配 |
| 实现复杂度 | 一个 ToolRegistry 三套注册逻辑 | 三个 Registry 类 |

**选择：合一。**
- 理由：工具来源对 Agent 应该完全透明——Agent 只知道有一个叫 "search" 的工具，不关心里面是本地函数还是 MCP 远程服务。
- 代价：`ToolRegistry` 内部需要维护多个 dict（`_tools` / `_functions` / `_mcp_tools`），但外部接口只有一个 `execute_tool()`。

---

## 决策 5：异常不中断 Agent 循环 vs 异常上抛终止

**背景**：工具执行可能失败（网络超时、API 限流、参数错误）。失败后怎么办？

| 维度 | 返回 ToolResult(success=False)，循环继续 | 异常上抛，Agent 终止 |
|------|------|------|
| 鲁棒性 | ✅ 一个工具失败不影响整体任务 | ❌ 任何工具失败 → 整个 Agent 崩溃 |
| 多步任务 | ✅ 搜索失败 → LLM 可以选择算数来间接推断 | ❌ 任务中断 |
| 用户感知 | 最终答案可能包含"部分信息无法获取" | 用户只看到异常堆栈 |
| LLM 上下文 | ✅ 错误信息作为 Observation 注入，LLM 看到后调整策略 | 无 |

**选择：返回 ToolResult(success=False)，循环继续。**
- 理由：真实场景中工具失败很常见（网络波动、API Key 过期），Agent 应该像人一样——一个工具不行换一个方式，而不是原地崩溃。
- 代价：需要在 `execute_tool()` 内部 try/except，Agent 层需要判断 `tool_result.success` 来决定 Observation 内容。

---

## 决策 6：B 阶段（原型）+ C 阶段（加固）两阶段策略

**背景**：先实现核心逻辑，再统一注入框架层特性（Config、异常体系、custom_prompt、pip install）。

为什么不一步到位？

| 维度 | 两阶段（B原型 → C加固） | 一步到位 |
|------|------|------|
| 每步复杂度 | 低——每次只关注一件事 | 高——同时考虑核心逻辑 + 框架层 |
| 调试 | B 阶段代码少，问题好定位 | 问题可能来自核心逻辑或框架层，排查困难 |
| CC 执行质量 | ✅ 每个任务边界清晰 | ❌ 混合关注点，容易写出半成品 |
| 重复代码 | B 到 C 需要"加固"一轮 | 一次写完 |

**选择：两阶段。**
- 理由：让 CC 在 B 阶段专注"让 Agent 跑起来"，C 阶段专注"让 Agent 像框架产品"。关注点分离 = 更少的 bug。
- 代价：C 阶段的任务看起来和 B 阶段像是"重复劳动"。实际上不是——B 阶段写新代码，C 阶段在已有代码上做增量注入。

---

## 与业界框架的关键对比（速度参考）

| 场景 | LangChain 代码量 | Kagent 代码量 |
|------|-----------------|-------------|
| 初始化一个带工具的 Agent | ~25 行（定义 LLM + 定义工具 + 创建 AgentExecutor） | ~6 行（AgentLLM + Tool + ReActAgent） |
| 切换 LLM | 改 import + 改初始化（~3 行） | 改 .env 一行 |
| 查看执行链路 | 需要注册 LangSmith / 自定义 Callback（~15 行） | `print(TraceExporter.to_tree(tracer.get_current_trace()))`（1 行） |
| 添加自定义工具 | @tool 装饰器（~3 行） | 实现 Tool 基类 / 直接 register_function（~5 行） |
