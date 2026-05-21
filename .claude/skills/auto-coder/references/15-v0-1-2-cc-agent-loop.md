## 15. V0.1.2 — CC 四相 Agent Loop

> **版本状态：已完成（2026-05-19）** — loop 按 CC 节奏运行；`steps` 使用四相可观察协议。

### 15.1 范式说明

Claude Code 核心节奏：

```text
THINK  : model reads messages + tools, produces assistant message
CALL   : runtime extracts tool_use blocks
OBSERVE: runtime executes tools, appends tool_result
LOOP   : model continues until no more tool_use → FINAL
```

- **控制流**由 `runtime/loop.py` + `messages` 历史驱动（真 loop）。
- **`AgentStep` 四相**（`think` / `call` / `observe` / `final`）是对该流程的**可观察投影**，供 API / 前端 / debug CLI；不替代底层 `tool_use` / `tool_result` 消息协议。
- **`observe` 的真载荷**是写入 `messages` 的 `ToolResultBlock`（`role=user`）；`AgentStep(type=observe)` 仅用于 `steps` / trace 展示。
- **`think` 只记录可见 assistant 文本**，不是隐藏 chain-of-thought：
  - **API / 默认 loop**（`plan_before_act=False`）：来自同一次 `call_model` 的 `response.text`；若仅有 `tool_use` 无文字，则 `steps` 使用固定占位摘要。
  - **Debug CLI**（`plan_before_act=True`）：每轮先 **无工具** 调用，强制 1～4 句计划，再进入 act（见 §17）。

### 15.2 Step 协议（已实现）

```python
class AgentStep(BaseModel):
    type: Literal["think", "call", "observe", "final"]
    turn_index: int
    content: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    is_error: bool = False
```

典型工具路径：`think → call → observe → think → final`  
纯文本路径：`think → final`

### 15.3 实现进度表（V0.1.2）

| ID | 任务 | 状态 | 实现位置 | 验证 |
| --- | --- | --- | --- | --- |
| V0.1.2-1 | `AgentStep` 四相协议 | [x] | `backend/app/runtime/messages.py` | `tests/test_agent_step.py` |
| V0.1.2-2 | loop 产出四相 `steps` | [x] | `backend/app/runtime/loop.py` | `tests/test_agent_loop.py` |
| V0.1.2-3 | 底层 message 协议不变 | [x] | `messages.py`, `loop.py` | 工具测试不回归 |
| V0.1.2-4 | debug_cli 打印 THINK/CALL/OBSERVE/FINAL | [x] | `backend/app/cli/debug.py` | `tests/test_debug_cli.py` |
| V0.1.2-5 | 纯文本 `think → final` | [x] | `tests/test_agent_loop.py` | `test_agent_pure_text_think_then_final` |
| V0.1.2-6 | 工具路径四相序列 | [x] | `tests/test_agent_loop.py` | calculator / read_file |
| V0.1.2-7 | 工具失败 `observe(is_error=True)` | [x] | `tests/test_agent_loop.py` | `test_agent_tool_error_observe` |
