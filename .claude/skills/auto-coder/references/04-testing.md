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
