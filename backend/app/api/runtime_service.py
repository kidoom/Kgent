"""Background agent run execution for HTTP transport."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.model_client import ModelClientError, ModelClientProtocol
from app.memory.persistence import PersistenceService
from app.runtime.loop import RunCancelledError, run_agent_stream
from app.runtime.messages import Message
from app.runtime.protocol import AgentEvent
from app.runtime.run_manager import RunManager, RunManagerError, RunManagerHost
from app.runtime.permissions import PermissionPolicy
from app.runtime.todo_state import TodoStateStore

TITLE_PROMPT = (
    "Summarize the conversation above into a very short title (5-8 words) "
    "that captures the main topic. Reply with ONLY the title text, no quotes, no punctuation at the end."
)

_active_tasks: dict[str, asyncio.Task[None]] = {}


async def _record_run_failed(
    *,
    run_manager: RunManager,
    run_id: str,
    session_id: str,
    error: str,
) -> None:
    state = run_manager.get_run(run_id)
    seq = (state.seq + 1) if state else 1
    failed = AgentEvent(
        type="run_failed",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={"error": error},
    )
    try:
        await run_manager.record_event(failed)
    except RunManagerError:
        if state:
            state.status = "failed"
            state.error = error
            run_manager._discard_connection_run(state)  # noqa: SLF001
            run_manager._clear_session_active_run(session_id, run_id)  # noqa: SLF001


async def execute_run(
    *,
    run_manager: RunManager,
    run_id: str,
    session_id: str,
    message: str,
    model_client: ModelClientProtocol,
    tools: list,
    policy: PermissionPolicy,
    max_steps: int,
    max_session_messages: int,
    project_root: Path,
    persistence: PersistenceService | None = None,
    todo_state_store: TodoStateStore | None = None,
) -> None:
    host = RunManagerHost(run_manager, run_id, session_id)
    try:
        await run_agent_stream(
            run_id=run_id,
            session_id=session_id,
            message=message,
            model_client=model_client,
            tools=tools,
            host=host,
            policy=policy,
            max_steps=max_steps,
            max_session_messages=max_session_messages,
            project_root=project_root,
            persistence=persistence,
            todo_state_store=todo_state_store,
        )
        await _maybe_generate_title(
            model_client=model_client,
            persistence=persistence,
            session_id=session_id,
        )
    except RunCancelledError:
        pass
    except ModelClientError as exc:
        await _record_run_failed(
            run_manager=run_manager,
            run_id=run_id,
            session_id=session_id,
            error=str(exc),
        )
    except RuntimeError as exc:
        await _record_run_failed(
            run_manager=run_manager,
            run_id=run_id,
            session_id=session_id,
            error=str(exc),
        )
    except RunManagerError as exc:
        await _record_run_failed(
            run_manager=run_manager,
            run_id=run_id,
            session_id=session_id,
            error=str(exc),
        )
    finally:
        _active_tasks.pop(run_id, None)


async def _maybe_generate_title(
    *,
    model_client: ModelClientProtocol,
    persistence: PersistenceService | None,
    session_id: str,
) -> None:
    if persistence is None or persistence.disabled:
        return

    meta = persistence.get_session(session_id)
    if meta is None:
        return

    if meta.first_prompt and meta.title != meta.first_prompt[:60]:
        return

    messages, _warnings = persistence.hydrate_messages(session_id)
    if not messages:
        return

    conversation_text = _build_title_conversation(messages)
    if not conversation_text.strip():
        return

    try:
        title_messages = [
            Message(role="user", content=f"{conversation_text}\n\n{TITLE_PROMPT}"),
        ]
        response = await model_client.call_model(title_messages, tools=[])
        title = (response.text or "").strip()
        if title and len(title) <= 80:
            persistence.append_session_meta(session_id, {"title": title})
    except (ModelClientError, RuntimeError, OSError):
        pass


def _build_title_conversation(messages: list[Message], max_chars: int = 1200) -> str:
    parts: list[str] = []
    total = 0
    for msg in messages:
        if msg.is_meta:
            continue
        if msg.role == "user" and isinstance(msg.content, str):
            label = "User"
            text = msg.content
        elif msg.role == "assistant" and isinstance(msg.content, str):
            label = "Assistant"
            text = msg.content
        else:
            continue
        snippet = text[:500]
        line = f"{label}: {snippet}"
        if total + len(line) > max_chars:
            break
        parts.append(line)
        total += len(line)
    return "\n".join(parts)


def schedule_run(**kwargs) -> asyncio.Task[None]:
    task = asyncio.create_task(execute_run(**kwargs))
    _active_tasks[kwargs["run_id"]] = task
    task.add_done_callback(lambda _t, rid=kwargs["run_id"]: _active_tasks.pop(rid, None))
    return task


def cancel_task(run_id: str) -> None:
    task = _active_tasks.pop(run_id, None)
    if task is not None and not task.done():
        task.cancel()
