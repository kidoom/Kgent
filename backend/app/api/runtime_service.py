"""Background agent run execution for HTTP transport."""

from __future__ import annotations

import asyncio

from app.model_client import ModelClientError, ModelClientProtocol
from app.runtime.loop import RunCancelledError, run_agent_stream
from app.runtime.protocol import AgentEvent, error_event
from app.runtime.run_manager import RunManager, RunManagerHost
from app.runtime.permissions import PermissionPolicy


_active_tasks: dict[str, asyncio.Task[None]] = {}


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
        )
    except RunCancelledError:
        pass
    except ModelClientError as exc:
        state = run_manager.get_run(run_id)
        seq = (state.seq + 1) if state else 1
        await run_manager.record_event(
            error_event(
                run_id=run_id,
                session_id=session_id,
                seq=seq,
                error=str(exc),
            )
        )
        if state:
            state.status = "failed"
    except RuntimeError as exc:
        state = run_manager.get_run(run_id)
        seq = (state.seq + 1) if state else 1
        await run_manager.record_event(
            AgentEvent(
                type="run_failed",
                run_id=run_id,
                session_id=session_id,
                seq=seq,
                payload={"error": str(exc)},
            )
        )
    finally:
        _active_tasks.pop(run_id, None)


def schedule_run(**kwargs) -> asyncio.Task[None]:
    task = asyncio.create_task(execute_run(**kwargs))
    _active_tasks[kwargs["run_id"]] = task
    task.add_done_callback(lambda _t, rid=kwargs["run_id"]: _active_tasks.pop(rid, None))
    return task


def cancel_task(run_id: str) -> None:
    task = _active_tasks.pop(run_id, None)
    if task is not None and not task.done():
        task.cancel()
