"""The minimal model-tool-model loop controller (CC think-call-observe paradigm)."""

from collections.abc import Callable

from app.agent.messages import (
    AgentResult,
    AgentStep,
    Message,
    ModelResponse,
    ToolExecutionResult,
    ToolResultBlock,
    ToolUseBlock,
)
from app.agent.model_client import ModelClient
from app.agent.prompts import PLAN_TURN_USER_PROMPT
from app.agent.session_store import get_or_create_session, trim_session_messages
from app.tools.base import Tool
from app.tools.registry import build_tool_schemas, find_tool_by_name

PLAN_FALLBACK_TEXT = "（计划阶段未返回可见文字，将继续进入工具/作答阶段。）"
THINK_WITHOUT_VISIBLE_TEXT = (
    "（本回合 API 未返回可见文字，仅 tool_use；非模型隐藏推理。）"
)

# event, turn_index (-1 if N/A), messages snapshot, steps appended at this checkpoint
AgentTraceCallback = Callable[[str, int, list[Message], list[AgentStep]], None]


def _emit_trace(
    on_trace: AgentTraceCallback | None,
    event: str,
    turn_index: int,
    messages: list[Message],
    added_steps: list[AgentStep] | None = None,
) -> None:
    if on_trace is not None:
        on_trace(event, turn_index, messages, added_steps or [])


async def _run_plan_phase(
    model_client: ModelClient,
    messages: list[Message],
    turn_index: int,
) -> AgentStep:
    """Text-only plan step (debug CLI). Ephemeral runtime prompt is not stored in session."""
    plan_messages = [*messages, Message(role="user", content=PLAN_TURN_USER_PROMPT)]
    response = await model_client.call_model(plan_messages, tools=[])
    plan_text = (response.text or "").strip() or PLAN_FALLBACK_TEXT
    messages.append(Message(role="assistant", content=plan_text))
    return AgentStep(type="think", turn_index=turn_index, content=plan_text)


async def run_agent(
    user_input: str,
    model_client: ModelClient,
    tools: list[Tool],
    max_steps: int = 8,
    session_id: str = "default",
    max_session_messages: int | None = None,
    on_trace: AgentTraceCallback | None = None,
    *,
    plan_before_act: bool = False,
) -> AgentResult:
    messages = get_or_create_session(session_id)
    messages.append(Message(role="user", content=user_input))
    if max_session_messages is not None:
        trim_session_messages(messages, max_session_messages)
    _emit_trace(on_trace, "after_user_append", -1, messages)

    steps: list[AgentStep] = []
    tool_schemas = build_tool_schemas(tools)

    for turn_index in range(max_steps):
        _emit_trace(on_trace, "turn_begin", turn_index, messages)
        if max_session_messages is not None:
            trim_session_messages(messages, max_session_messages)

        if plan_before_act:
            think_step = await _run_plan_phase(model_client, messages, turn_index)
            steps.append(think_step)
            _emit_trace(on_trace, "after_plan", turn_index, messages, [think_step])
            response = await model_client.call_model(messages=messages, tools=tool_schemas)
            messages.append(response.assistant_message)
            _emit_trace(on_trace, "after_act", turn_index, messages)
        else:
            response = await _run_standard_turn(model_client, messages, tool_schemas, turn_index, steps, on_trace)

        if not response.tool_uses:
            final_step = AgentStep(
                type="final",
                turn_index=turn_index,
                content=response.text,
            )
            steps.append(final_step)
            _emit_trace(on_trace, "complete", turn_index, messages, [final_step])
            return AgentResult(
                answer=response.text,
                steps=steps,
                session_id=session_id,
                message_count=len(messages),
            )

        for tool_use in response.tool_uses:
            call_step = AgentStep(
                type="call",
                turn_index=turn_index,
                tool_use_id=tool_use.id,
                tool_name=tool_use.name,
                tool_input=dict(tool_use.input),
            )
            steps.append(call_step)
            result = await execute_tool_use(tool_use, tools)
            observe_step = AgentStep(
                type="observe",
                turn_index=turn_index,
                tool_use_id=tool_use.id,
                tool_name=tool_use.name,
                content=result.content,
                is_error=result.is_error,
            )
            steps.append(observe_step)
            messages.append(
                Message(
                    role="user",
                    content=[
                        ToolResultBlock(
                            tool_use_id=tool_use.id,
                            content=result.content,
                            is_error=result.is_error,
                        )
                    ],
                )
            )
            _emit_trace(
                on_trace,
                "after_tool",
                turn_index,
                messages,
                [call_step, observe_step],
            )

    raise RuntimeError("Agent stopped: max steps reached")


async def _run_standard_turn(
    model_client: ModelClient,
    messages: list[Message],
    tool_schemas: list[dict],
    turn_index: int,
    steps: list[AgentStep],
    on_trace: AgentTraceCallback | None,
) -> ModelResponse:
    response = await model_client.call_model(messages=messages, tools=tool_schemas)
    messages.append(response.assistant_message)

    turn_steps: list[AgentStep] = []
    if response.text:
        think_step = AgentStep(
            type="think",
            turn_index=turn_index,
            content=response.text,
        )
        steps.append(think_step)
        turn_steps.append(think_step)
    _emit_trace(on_trace, "after_model", turn_index, messages, turn_steps)

    if response.tool_uses and not response.text:
        placeholder_think = AgentStep(
            type="think",
            turn_index=turn_index,
            content=THINK_WITHOUT_VISIBLE_TEXT,
        )
        steps.append(placeholder_think)
        _emit_trace(on_trace, "after_think_placeholder", turn_index, messages, [placeholder_think])

    return response


async def execute_tool_use(tool_use: ToolUseBlock, tools: list[Tool]) -> ToolExecutionResult:
    tool = find_tool_by_name(tools, tool_use.name)
    if tool is None:
        return ToolExecutionResult(content=f"Unknown tool: {tool_use.name}", is_error=True)

    try:
        content = await tool.call(tool_use.input)
        return ToolExecutionResult(content=content)
    except Exception as exc:  # noqa: BLE001 - errors are returned to the model deliberately.
        return ToolExecutionResult(content=f"Error: {exc}", is_error=True)
