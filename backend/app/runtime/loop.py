"""The minimal model-tool-model loop controller (CC think-call-observe paradigm)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.runtime.context_builder import build_model_messages
from app.runtime.context_compression import (
    CompressionConfig,
    estimate_messages_tokens,
    execute_compact,
    get_token_calibrator,
    micro_compact_messages,
    should_auto_compact,
)
from app.runtime.compact_prompt import COMPACT_SYSTEM_PROMPT, compact_user_prompt
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
from app.model_client import ModelClient, PromptTooLongError
from app.runtime.permissions import AllowAllPolicy, PermissionPolicy
from app.runtime.prompts import PLAN_TURN_USER_PROMPT
from app.runtime.protocol import (
    agent_step_event,
    loop_checkpoint_event,
    run_finished_event,
    todo_state_event,
    tool_call_started_event,
    AgentEvent,
)
from app.memory.persistence import PersistenceError, PersistenceService
from app.memory.session_store import get_or_create_session, trim_session_messages
from app.runtime.todo_state import TodoStateStore
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


async def _emit_loop_trace(
    *,
    host: AgentHost | None,
    seq_counter: list[int] | None,
    run_id: str,
    session_id: str,
    on_trace: AgentTraceCallback | None,
    checkpoint: str,
    turn_index: int,
    messages: list[Message],
    added_steps: list[AgentStep] | None = None,
    tool_count: int | None = None,
    tool_schemas: list[dict[str, Any]] | None = None,
) -> None:
    _emit_trace(on_trace, checkpoint, turn_index, messages, added_steps)
    if host is None or seq_counter is None:
        return
    seq_counter[0] += 1
    await host.emit(
        loop_checkpoint_event(
            run_id=run_id,
            session_id=session_id,
            seq=seq_counter[0],
            checkpoint=checkpoint,
            turn_index=turn_index,
            messages=messages,
            added_steps=added_steps,
            tool_count=tool_count,
            tool_schemas=tool_schemas,
        )
    )


class RunCancelledError(Exception):
    """Raised when a run is cancelled mid-loop."""


def _persist_message(
    persistence: PersistenceService | None,
    session_id: str,
    message: Message,
    *,
    user_prompt: str | None = None,
) -> None:
    if persistence is None:
        return
    try:
        persistence.append_message(session_id, message, user_prompt=user_prompt)
    except PersistenceError as exc:
        raise RuntimeError(str(exc)) from exc


def _messages_with_todo_reminder(
    messages: list[Message],
    *,
    todo_state_store: TodoStateStore | None,
    session_id: str,
) -> list[Message]:
    if todo_state_store is None:
        return messages
    reminder = todo_state_store.reminder_message(session_id)
    if reminder is None:
        return messages
    return [*messages, reminder]


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
    *,
    project_root: Path,
    persistence: PersistenceService | None,
    session_id: str,
    todo_state_store: TodoStateStore | None = None,
    compression_config: CompressionConfig | None = None,
    model_identity: str | None = None,
) -> AgentStep:
    """Text-only plan step (debug CLI). Ephemeral runtime prompt is not stored in session."""
    cfg = compression_config or CompressionConfig()
    plan_messages = [*messages, Message(role="user", content=PLAN_TURN_USER_PROMPT)]
    request_messages = build_model_messages(plan_messages, project_root=project_root)
    if cfg.context_compression_enabled and cfg.micro_compact_enabled:
        request_messages = micro_compact_messages(
            request_messages,
            keep_recent=cfg.keep_recent_tool_results,
            min_chars=cfg.micro_compact_min_chars,
        )

    # AutoCompact: summarize session when approaching context window.
    local_estimate = estimate_messages_tokens(request_messages)
    calibrated = local_estimate
    if model_identity:
        provider, _, model = model_identity.partition("/")
        calibrated = get_token_calibrator().calibrated_estimate(provider, model, local_estimate)
    if cfg.context_compression_enabled and cfg.auto_compact_enabled and should_auto_compact(
        request_messages,
        context_window_tokens=cfg.context_window_tokens,
        auto_compact_buffer_tokens=cfg.auto_compact_buffer_tokens,
        compact_max_summary_tokens=cfg.compact_max_summary_tokens,
        calibrated_token_estimate=calibrated,
    ):
        try:
            request_messages = await _compact_and_rebuild(
                model_client=model_client,
                messages=messages,
                reason="auto_compact",
                session_id=session_id,
                project_root=project_root,
                persistence=persistence,
                todo_state_store=todo_state_store,
                compression_config=compression_config,
            )
            # Rebuild plan request after compact.
            plan_messages = [*messages, Message(role="user", content=PLAN_TURN_USER_PROMPT)]
            request_messages = build_model_messages(plan_messages, project_root=project_root)
            if cfg.context_compression_enabled and cfg.micro_compact_enabled:
                request_messages = micro_compact_messages(
                    request_messages,
                    keep_recent=cfg.keep_recent_tool_results,
                    min_chars=cfg.micro_compact_min_chars,
                )
        except Exception:
            pass  # Compact failure is non-fatal.

    try:
        response = await model_client.call_model(request_messages, tools=[])
    except PromptTooLongError:
        if not cfg.context_compression_enabled or not cfg.reactive_compact_enabled:
            raise
        await _compact_and_rebuild(
            model_client=model_client,
            messages=messages,
            reason="reactive_compact",
            session_id=session_id,
            project_root=project_root,
            persistence=persistence,
            todo_state_store=todo_state_store,
            compression_config=compression_config,
        )
        plan_messages = [*messages, Message(role="user", content=PLAN_TURN_USER_PROMPT)]
        request_messages = build_model_messages(plan_messages, project_root=project_root)
        response = await model_client.call_model(request_messages, tools=[])

    plan_text = (response.text or "").strip() or PLAN_FALLBACK_TEXT
    assistant_message = Message(role="assistant", content=plan_text)
    messages.append(assistant_message)
    _persist_message(persistence, session_id, assistant_message)
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
    project_root: Path | None = None,
    persistence: PersistenceService | None = None,
    todo_state_store: TodoStateStore | None = None,
    compression_config: CompressionConfig | None = None,
    model_identity: str | None = None,
) -> AgentResult:
    if policy is None:
        policy = AllowAllPolicy()
    cfg = compression_config or CompressionConfig()
    effective_project_root = _infer_project_root(tools, project_root)

    seq_counter = [1]
    await host.emit(make_run_started_event(run_id, session_id))
    seq_counter[0] = 2

    messages = get_or_create_session(session_id)
    user_message = Message(role="user", content=message)
    messages.append(user_message)
    _persist_message(persistence, session_id, user_message, user_prompt=message)
    if max_session_messages is not None:
        trim_session_messages(messages, max_session_messages)
    await _emit_loop_trace(
        host=host,
        seq_counter=seq_counter,
        run_id=run_id,
        session_id=session_id,
        on_trace=on_trace,
        checkpoint="after_user_append",
        turn_index=-1,
        messages=messages,
    )

    steps: list[AgentStep] = []
    tool_schemas = build_tool_schemas(tools)

    try:
        for turn_index in range(max_steps):
            if await host.check_cancelled():
                raise RunCancelledError()

            await _emit_loop_trace(
                host=host,
                seq_counter=seq_counter,
                run_id=run_id,
                session_id=session_id,
                on_trace=on_trace,
                checkpoint="turn_begin",
                turn_index=turn_index,
                messages=messages,
            )
            if max_session_messages is not None:
                trim_session_messages(messages, max_session_messages)

            if plan_before_act:
                plan_messages = [*messages, Message(role="user", content=PLAN_TURN_USER_PROMPT)]
                await _emit_loop_trace(
                    host=host,
                    seq_counter=seq_counter,
                    run_id=run_id,
                    session_id=session_id,
                    on_trace=on_trace,
                    checkpoint="before_plan_call",
                    turn_index=turn_index,
                    messages=build_model_messages(plan_messages, project_root=effective_project_root),
                    tool_count=0,
                )
                think_step = await _run_plan_phase(
                    model_client,
                    messages,
                    turn_index,
                    project_root=effective_project_root,
                    persistence=persistence,
                    session_id=session_id,
                    todo_state_store=todo_state_store,
                    compression_config=compression_config,
                    model_identity=model_identity,
                )
                steps.append(think_step)
                seq_counter[0] += 1
                await _emit_step(
                    host,
                    run_id=run_id,
                    session_id=session_id,
                    seq=seq_counter[0],
                    step=think_step,
                )
                await _emit_loop_trace(
                    host=host,
                    seq_counter=seq_counter,
                    run_id=run_id,
                    session_id=session_id,
                    on_trace=on_trace,
                    checkpoint="after_plan",
                    turn_index=turn_index,
                    messages=messages,
                    added_steps=[think_step],
                )
                await _emit_loop_trace(
                    host=host,
                    seq_counter=seq_counter,
                    run_id=run_id,
                    session_id=session_id,
                    on_trace=on_trace,
                    checkpoint="before_model_call",
                    turn_index=turn_index,
                    messages=build_model_messages(messages, project_root=effective_project_root),
                    tool_count=len(tool_schemas),
                    tool_schemas=tool_schemas,
                )
                act_request = build_model_messages(messages, project_root=effective_project_root)
                if cfg.context_compression_enabled and cfg.micro_compact_enabled:
                    act_request = micro_compact_messages(
                        act_request,
                        keep_recent=cfg.keep_recent_tool_results,
                        min_chars=cfg.micro_compact_min_chars,
                    )

                # AutoCompact: summarize session when approaching context window.
                local_estimate = estimate_messages_tokens(act_request)
                calibrated = local_estimate
                if model_identity:
                    provider, _, model = model_identity.partition("/")
                    calibrated = get_token_calibrator().calibrated_estimate(provider, model, local_estimate)
                if cfg.context_compression_enabled and cfg.auto_compact_enabled and should_auto_compact(
                    act_request,
                    context_window_tokens=cfg.context_window_tokens,
                    auto_compact_buffer_tokens=cfg.auto_compact_buffer_tokens,
                    compact_max_summary_tokens=cfg.compact_max_summary_tokens,
                    calibrated_token_estimate=calibrated,
                ):
                    try:
                        act_request = await _compact_and_rebuild(
                            model_client=model_client,
                            messages=messages,
                            reason="auto_compact",
                            session_id=session_id,
                            project_root=effective_project_root,
                            persistence=persistence,
                            todo_state_store=todo_state_store,
                            compression_config=compression_config,
                        )
                    except Exception:
                        pass  # Compact failure is non-fatal.

                try:
                    response = await model_client.call_model(
                        messages=act_request,
                        tools=tool_schemas,
                    )
                except PromptTooLongError:
                    if not cfg.context_compression_enabled or not cfg.reactive_compact_enabled:
                        raise
                    act_request = await _compact_and_rebuild(
                        model_client=model_client,
                        messages=messages,
                        reason="reactive_compact",
                        session_id=session_id,
                        project_root=effective_project_root,
                        persistence=persistence,
                        todo_state_store=todo_state_store,
                        compression_config=compression_config,
                    )
                    response = await model_client.call_model(
                        messages=act_request,
                        tools=tool_schemas,
                    )
                messages.append(response.assistant_message)
                _persist_message(persistence, session_id, response.assistant_message)
                await _emit_loop_trace(
                    host=host,
                    seq_counter=seq_counter,
                    run_id=run_id,
                    session_id=session_id,
                    on_trace=on_trace,
                    checkpoint="after_act",
                    turn_index=turn_index,
                    messages=messages,
                )
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
                    project_root=effective_project_root,
                    persistence=persistence,
                    todo_state_store=todo_state_store,
                    compression_config=compression_config,
                    model_identity=model_identity,
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
                await _emit_loop_trace(
                    host=host,
                    seq_counter=seq_counter,
                    run_id=run_id,
                    session_id=session_id,
                    on_trace=on_trace,
                    checkpoint="complete",
                    turn_index=turn_index,
                    messages=messages,
                    added_steps=[final_step],
                )
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

            used_todo_write = any(tool_use.name == "todo_write" for tool_use in response.tool_uses)
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
                    await _emit_loop_trace(
                        host=host,
                        seq_counter=seq_counter,
                        run_id=run_id,
                        session_id=session_id,
                        on_trace=on_trace,
                        checkpoint="after_permission",
                        turn_index=turn_index,
                        messages=messages,
                        added_steps=[call_step],
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
                    if tool_use.name == "todo_write" and not result.is_error and todo_state_store is not None:
                        seq_counter[0] += 1
                        await host.emit(
                            todo_state_event(
                                run_id=run_id,
                                session_id=session_id,
                                seq=seq_counter[0],
                                state=todo_state_store.get_state(session_id).model_dump(mode="json"),
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
                tool_result_message = Message(
                    role="tool",
                    content=[
                        ToolResultBlock(
                            tool_use_id=tool_use.id,
                            content=result.content,
                            is_error=result.is_error,
                        )
                    ],
                )
                messages.append(tool_result_message)
                _persist_message(persistence, session_id, tool_result_message)
                await _emit_loop_trace(
                    host=host,
                    seq_counter=seq_counter,
                    run_id=run_id,
                    session_id=session_id,
                    on_trace=on_trace,
                    checkpoint="after_tool",
                    turn_index=turn_index,
                    messages=messages,
                    added_steps=[call_step, observe_step],
                )

            if todo_state_store is not None and not used_todo_write:
                todo_state_store.record_model_turn_without_todo_write(session_id)

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
    project_root: Path | None = None,
    persistence: PersistenceService | None = None,
    todo_state_store: TodoStateStore | None = None,
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
        project_root=project_root,
        persistence=persistence,
        todo_state_store=todo_state_store,
    )
    return host.to_agent_result()


async def _compact_and_rebuild(
    *,
    model_client: ModelClient,
    messages: list[Message],
    reason: str,
    session_id: str,
    project_root: Path,
    persistence: PersistenceService | None,
    todo_state_store: TodoStateStore | None,
    compression_config: CompressionConfig | None = None,
) -> list[Message]:
    """Summarize session, replace in-memory messages, rebuild request view."""
    cfg = compression_config or CompressionConfig()

    def _rebuild(msgs: list[Message]) -> list[Message]:
        request_session_messages = _messages_with_todo_reminder(
            msgs,
            todo_state_store=todo_state_store,
            session_id=session_id,
        )
        req = build_model_messages(request_session_messages, project_root=project_root)
        if cfg.context_compression_enabled and cfg.micro_compact_enabled:
            req = micro_compact_messages(
                req,
                keep_recent=cfg.keep_recent_tool_results,
                min_chars=cfg.micro_compact_min_chars,
            )
        return req

    def _persist(sid: str, payload: dict) -> None:
        if persistence is not None:
            persistence.append_summary(sid, payload)

    def _on_event(*_a: Any, **_kw: Any) -> None:
        pass  # Telemetry sink — transcript persistence covers audit.

    return await execute_compact(
        model_client=model_client,
        messages=messages,
        reason=reason,
        compact_system_prompt=COMPACT_SYSTEM_PROMPT,
        compact_user_prompt_text=compact_user_prompt(len(messages)),
        keep_recent_messages=cfg.compact_keep_recent_messages,
        persist_fn=_persist,
        session_id=session_id,
        rebuild_request_fn=_rebuild,
        on_compact_event=_on_event,
    )


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
    project_root: Path | None = None,
    persistence: PersistenceService | None = None,
    todo_state_store: TodoStateStore | None = None,
    compression_config: CompressionConfig | None = None,
    model_identity: str | None = None,
) -> ModelResponse:
    effective_project_root = _infer_project_root([], project_root)
    cfg = compression_config or CompressionConfig()
    request_session_messages = _messages_with_todo_reminder(
        messages,
        todo_state_store=todo_state_store,
        session_id=session_id,
    )
    request_messages = build_model_messages(request_session_messages, project_root=effective_project_root)
    if cfg.context_compression_enabled and cfg.micro_compact_enabled:
        request_messages = micro_compact_messages(
            request_messages,
            keep_recent=cfg.keep_recent_tool_results,
            min_chars=cfg.micro_compact_min_chars,
        )

    # AutoCompact: summarize session when approaching context window.
    local_estimate = estimate_messages_tokens(request_messages)
    calibrated = local_estimate
    if model_identity:
        provider, _, model = model_identity.partition("/")
        calibrated = get_token_calibrator().calibrated_estimate(provider, model, local_estimate)
    if cfg.context_compression_enabled and cfg.auto_compact_enabled and should_auto_compact(
        request_messages,
        context_window_tokens=cfg.context_window_tokens,
        auto_compact_buffer_tokens=cfg.auto_compact_buffer_tokens,
        compact_max_summary_tokens=cfg.compact_max_summary_tokens,
        calibrated_token_estimate=calibrated,
    ):
        try:
            request_messages = await _compact_and_rebuild(
                model_client=model_client,
                messages=messages,
                reason="auto_compact",
                session_id=session_id,
                project_root=effective_project_root,
                persistence=persistence,
                todo_state_store=todo_state_store,
                compression_config=compression_config,
            )
        except Exception:
            pass  # Compact failure is non-fatal; proceed with original messages.

    await _emit_loop_trace(
        host=host,
        seq_counter=seq_counter,
        run_id=run_id,
        session_id=session_id,
        on_trace=on_trace,
        checkpoint="before_model_call",
        turn_index=turn_index,
        messages=request_messages,
        tool_count=len(tool_schemas),
        tool_schemas=tool_schemas,
    )
    try:
        response = await model_client.call_model(messages=request_messages, tools=tool_schemas)
    except PromptTooLongError:
        if not cfg.context_compression_enabled or not cfg.reactive_compact_enabled:
            raise
        request_messages = await _compact_and_rebuild(
            model_client=model_client,
            messages=messages,
            reason="reactive_compact",
            session_id=session_id,
            project_root=effective_project_root,
            persistence=persistence,
            todo_state_store=todo_state_store,
            compression_config=compression_config,
        )
        response = await model_client.call_model(messages=request_messages, tools=tool_schemas)

    # Record usage for calibration.
    if model_identity and response.usage and response.usage.prompt_tokens:
        provider, _, model = model_identity.partition("/")
        get_token_calibrator().record(
            provider,
            model,
            estimated_tokens=local_estimate,
            actual_prompt_tokens=response.usage.prompt_tokens,
        )

    messages.append(response.assistant_message)
    _persist_message(persistence, session_id, response.assistant_message)

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
    await _emit_loop_trace(
        host=host,
        seq_counter=seq_counter,
        run_id=run_id,
        session_id=session_id,
        on_trace=on_trace,
        checkpoint="after_model",
        turn_index=turn_index,
        messages=messages,
        added_steps=turn_steps,
    )

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
        await _emit_loop_trace(
            host=host,
            seq_counter=seq_counter,
            run_id=run_id,
            session_id=session_id,
            on_trace=on_trace,
            checkpoint="after_think_placeholder",
            turn_index=turn_index,
            messages=messages,
            added_steps=[placeholder_think],
        )

    return response


def _infer_project_root(tools: list[Tool], project_root: Path | None) -> Path:
    if project_root is not None:
        return project_root.resolve()
    for tool in tools:
        candidate = getattr(tool, "project_root", None)
        if isinstance(candidate, Path):
            return candidate.resolve()
    return Path.cwd().resolve()


async def execute_tool_use(tool_use: ToolUseBlock, tools: list[Tool]) -> ToolExecutionResult:
    tool = find_tool_by_name(tools, tool_use.name)
    if tool is None:
        return ToolExecutionResult(content=f"Unknown tool: {tool_use.name}", is_error=True)

    try:
        content = await tool.call(tool_use.input)
        return ToolExecutionResult(content=content)
    except Exception as exc:  # noqa: BLE001 - errors are returned to the model deliberately.
        return ToolExecutionResult(content=f"Error: {exc}", is_error=True)
