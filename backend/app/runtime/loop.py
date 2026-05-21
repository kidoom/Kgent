"""The minimal model-tool-model loop controller (CC think-call-observe paradigm)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from app.runtime.host import AgentHost, CollectingHost, build_permission_request, make_run_started_event
from app.runtime.messages import (
    AgentResult,
    AgentStep,
    Message,
    ModelResponse,
    ToolExecutionResult,
    ToolResultBlock,
    ToolUseBlock,
)
from app.model_client import ModelClient
from app.runtime.permissions import AllowAllPolicy, PermissionPolicy
from app.runtime.prompts import PLAN_TURN_USER_PROMPT
from app.runtime.protocol import (
    agent_step_event,
    run_finished_event,
    tool_call_started_event,
    AgentEvent,
)
from app.memory.session_store import get_or_create_session, trim_session_messages
from app.tools.base import Tool
from app.tools.registry import build_tool_schemas, find_tool_by_name

PLAN_FALLBACK_TEXT = "（计划阶段未返回可见文字，将继续进入工具/作答阶段。）"
THINK_WITHOUT_VISIBLE_TEXT = (
    "（本回合 API 未返回可见文字，仅 tool_use；非模型隐藏推理。）"
)
PERMISSION_DENIED_PREFIX = "permission_denied"


def _format_permission_denied(reason: str) -> str:
    reason = (reason or "").strip()
    if reason:
        return f"{PERMISSION_DENIED_PREFIX}: {reason}"
    return PERMISSION_DENIED_PREFIX


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


class RunCancelledError(Exception):
    """Raised when a run is cancelled mid-loop."""


async def _emit_step(
    host: AgentHost,
    *,
    run_id: str,
    session_id: str,
    seq: int,
    step: AgentStep,
) -> None:
    await host.emit(
        agent_step_event(
            run_id=run_id,
            session_id=session_id,
            seq=seq,
            step=step,
        )
    )


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


async def _resolve_tool_execution(
    *,
    tool: Tool | None,
    tool_use: ToolUseBlock,
    tools: list[Tool],
    policy: PermissionPolicy,
    host: AgentHost,
    run_id: str,
    session_id: str,
    seq_counter: list[int],
) -> tuple[str, ToolExecutionResult, AgentStep]:
    """Return (decision_action, result, call_step)."""
    if tool is None:
        return (
            "allow",
            ToolExecutionResult(content=f"Unknown tool: {tool_use.name}", is_error=True),
            AgentStep(
                type="call",
                turn_index=0,
                tool_use_id=tool_use.id,
                tool_name=tool_use.name,
                tool_input=dict(tool_use.input),
                decision="allow",
            ),
        )

    decision = await policy.decide(tool, tool_use)
    decision_action = decision.action

    if decision_action == "allow":
        result = await execute_tool_use(tool_use, tools)
    elif decision_action == "deny":
        result = ToolExecutionResult(
            content=_format_permission_denied(decision.reason),
            is_error=True,
        )
    elif decision_action == "ask":
        request = build_permission_request(
            run_id=run_id,
            session_id=session_id,
            tool_use_id=tool_use.id,
            tool_name=tool_use.name,
            risk_level=getattr(tool, "risk_level", "high"),
            tool_input=dict(tool_use.input),
            reason=decision.reason,
        )
        resolved = await host.request_permission(request)
        if await host.check_cancelled():
            raise RunCancelledError()
        if resolved.action == "allow":
            decision_action = "allow"
            result = await execute_tool_use(tool_use, tools)
        else:
            decision_action = "deny"
            result = ToolExecutionResult(
                content=_format_permission_denied(resolved.reason or "user rejected"),
                is_error=True,
            )
    else:
        decision_action = "deny"
        result = ToolExecutionResult(
            content=_format_permission_denied(decision.reason),
            is_error=True,
        )

    call_step = AgentStep(
        type="call",
        turn_index=0,
        tool_use_id=tool_use.id,
        tool_name=tool_use.name,
        tool_input=dict(tool_use.input),
        decision=decision_action,  # type: ignore[arg-type]
    )
    return decision_action, result, call_step


async def run_agent_stream(
    *,
    run_id: str,
    session_id: str,
    message: str,
    model_client: ModelClient,
    tools: list[Tool],
    host: AgentHost,
    policy: PermissionPolicy | None = None,
    max_steps: int = 8,
    max_session_messages: int | None = None,
    on_trace: AgentTraceCallback | None = None,
    plan_before_act: bool = False,
) -> AgentResult:
    if policy is None:
        policy = AllowAllPolicy()

    seq_counter = [1]
    await host.emit(make_run_started_event(run_id, session_id))
    seq_counter[0] = 2

    messages = get_or_create_session(session_id)
    messages.append(Message(role="user", content=message))
    if max_session_messages is not None:
        trim_session_messages(messages, max_session_messages)
    _emit_trace(on_trace, "after_user_append", -1, messages)

    steps: list[AgentStep] = []
    tool_schemas = build_tool_schemas(tools)

    try:
        for turn_index in range(max_steps):
            if await host.check_cancelled():
                raise RunCancelledError()

            _emit_trace(on_trace, "turn_begin", turn_index, messages)
            if max_session_messages is not None:
                trim_session_messages(messages, max_session_messages)

            if plan_before_act:
                think_step = await _run_plan_phase(model_client, messages, turn_index)
                steps.append(think_step)
                seq_counter[0] += 1
                await _emit_step(
                    host,
                    run_id=run_id,
                    session_id=session_id,
                    seq=seq_counter[0],
                    step=think_step,
                )
                _emit_trace(on_trace, "after_plan", turn_index, messages, [think_step])
                response = await model_client.call_model(messages=messages, tools=tool_schemas)
                messages.append(response.assistant_message)
                _emit_trace(on_trace, "after_act", turn_index, messages)
            else:
                response = await _run_standard_turn(
                    model_client,
                    messages,
                    tool_schemas,
                    turn_index,
                    steps,
                    on_trace,
                    host=host,
                    run_id=run_id,
                    session_id=session_id,
                    seq_counter=seq_counter,
                )

            if await host.check_cancelled():
                raise RunCancelledError()

            if not response.tool_uses:
                final_step = AgentStep(
                    type="final",
                    turn_index=turn_index,
                    content=response.text,
                )
                steps.append(final_step)
                seq_counter[0] += 1
                await _emit_step(
                    host,
                    run_id=run_id,
                    session_id=session_id,
                    seq=seq_counter[0],
                    step=final_step,
                )
                _emit_trace(on_trace, "complete", turn_index, messages, [final_step])
                result = AgentResult(
                    answer=response.text,
                    steps=steps,
                    session_id=session_id,
                    message_count=len(messages),
                )
                await host.emit(
                    run_finished_event(
                        run_id=run_id,
                        session_id=session_id,
                        seq=seq_counter[0] + 1,
                        answer=result.answer,
                        message_count=result.message_count,
                        steps=result.steps,
                    )
                )
                return result

            for tool_use in response.tool_uses:
                if await host.check_cancelled():
                    raise RunCancelledError()

                tool = find_tool_by_name(tools, tool_use.name)
                decision_action, result, call_step = await _resolve_tool_execution(
                    tool=tool,
                    tool_use=tool_use,
                    tools=tools,
                    policy=policy,
                    host=host,
                    run_id=run_id,
                    session_id=session_id,
                    seq_counter=seq_counter,
                )
                call_step.turn_index = turn_index
                steps.append(call_step)
                seq_counter[0] += 1
                await _emit_step(
                    host,
                    run_id=run_id,
                    session_id=session_id,
                    seq=seq_counter[0],
                    step=call_step,
                )

                if decision_action != "allow":
                    _emit_trace(
                        on_trace,
                        "after_permission",
                        turn_index,
                        messages,
                        [call_step],
                    )

                if decision_action == "allow":
                    seq_counter[0] += 1
                    await host.emit(
                        tool_call_started_event(
                            run_id=run_id,
                            session_id=session_id,
                            seq=seq_counter[0],
                            tool_use_id=tool_use.id,
                            tool_name=tool_use.name,
                            tool_input=dict(tool_use.input),
                        )
                    )

                observe_step = AgentStep(
                    type="observe",
                    turn_index=turn_index,
                    tool_use_id=tool_use.id,
                    tool_name=tool_use.name,
                    content=result.content,
                    is_error=result.is_error,
                )
                steps.append(observe_step)
                seq_counter[0] += 1
                await _emit_step(
                    host,
                    run_id=run_id,
                    session_id=session_id,
                    seq=seq_counter[0],
                    step=observe_step,
                )
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

    except RunCancelledError:
        await host.emit(
            AgentEvent(
                type="run_cancelled",
                run_id=run_id,
                session_id=session_id,
                seq=seq_counter[0] + 1,
                payload={},
            )
        )
        raise


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
    policy: PermissionPolicy | None = None,
    run_id: str | None = None,
) -> AgentResult:
    """Compatibility wrapper over run_agent_stream using CollectingHost."""
    rid = run_id or f"run_{uuid.uuid4().hex[:12]}"
    host = CollectingHost(run_id=rid, session_id=session_id, auto_resolve_ask=False)
    await run_agent_stream(
        run_id=rid,
        session_id=session_id,
        message=user_input,
        model_client=model_client,
        tools=tools,
        host=host,
        policy=policy,
        max_steps=max_steps,
        max_session_messages=max_session_messages,
        on_trace=on_trace,
        plan_before_act=plan_before_act,
    )
    return host.to_agent_result()


async def _run_standard_turn(
    model_client: ModelClient,
    messages: list[Message],
    tool_schemas: list[dict],
    turn_index: int,
    steps: list[AgentStep],
    on_trace: AgentTraceCallback | None,
    *,
    host: AgentHost | None = None,
    run_id: str = "",
    session_id: str = "default",
    seq_counter: list[int] | None = None,
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
        if host is not None and seq_counter is not None:
            seq_counter[0] += 1
            await _emit_step(
                host,
                run_id=run_id,
                session_id=session_id,
                seq=seq_counter[0],
                step=think_step,
            )
    _emit_trace(on_trace, "after_model", turn_index, messages, turn_steps)

    if response.tool_uses and not response.text:
        placeholder_think = AgentStep(
            type="think",
            turn_index=turn_index,
            content=THINK_WITHOUT_VISIBLE_TEXT,
        )
        steps.append(placeholder_think)
        if host is not None and seq_counter is not None:
            seq_counter[0] += 1
            await _emit_step(
                host,
                run_id=run_id,
                session_id=session_id,
                seq=seq_counter[0],
                step=placeholder_think,
            )
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
