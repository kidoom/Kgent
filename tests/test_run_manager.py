"""Tests for RunManager (V0.2.1)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.api import runtime_service
from app.memory.persistence import PersistenceError
from app.runtime.protocol import AgentEvent, PermissionRequest, ResolvedPermission, permission_required_event
from app.runtime.run_manager import (
    DEFAULT_SESSION_EVENT_MAX,
    RunManager,
    RunManagerError,
    _parse_session_event_max,
)


def test_parse_session_event_max_defaults() -> None:
    assert _parse_session_event_max(None) == DEFAULT_SESSION_EVENT_MAX
    assert _parse_session_event_max("") == DEFAULT_SESSION_EVENT_MAX
    assert _parse_session_event_max("   ") == DEFAULT_SESSION_EVENT_MAX
    assert _parse_session_event_max("not-a-number") == DEFAULT_SESSION_EVENT_MAX


def test_parse_session_event_max_clamps_minimum() -> None:
    assert _parse_session_event_max("3") == 50
    assert _parse_session_event_max("100") == 100


@pytest.mark.parametrize("raw", ["", "abc", "  "])
def test_run_manager_invalid_session_event_max_env(monkeypatch, raw: str) -> None:
    monkeypatch.setenv("KGENT_SESSION_EVENT_MAX", raw)
    manager = RunManager()
    assert manager._session_event_max == DEFAULT_SESSION_EVENT_MAX


def _make_request(run_id: str, perm_id: str = "perm_1") -> PermissionRequest:
    return PermissionRequest(
        permission_request_id=perm_id,
        run_id=run_id,
        session_id="default",
        tool_use_id="toolu_1",
        tool_name="read_file",
        risk_level="medium",
        tool_input={"path": "README.md"},
    )


@pytest.mark.asyncio
async def test_wait_for_permission_allow() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default")

    async def resolver() -> None:
        await asyncio.sleep(0.01)
        await manager.resolve_permission(
            run_id=run_id,
            permission_request_id="perm_1",
            decision="allow",
        )

    task = asyncio.create_task(resolver())
    result = await manager.wait_for_permission(_make_request(run_id))
    await task

    assert result.action == "allow"
    state = manager.get_run(run_id)
    assert state is not None
    assert state.status == "running"
    assert state.pending is None


@pytest.mark.asyncio
async def test_wait_for_permission_deny() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default")

    async def resolver() -> None:
        await asyncio.sleep(0.01)
        await manager.resolve_permission(
            run_id=run_id,
            permission_request_id="perm_1",
            decision="deny",
        )

    task = asyncio.create_task(resolver())
    result = await manager.wait_for_permission(_make_request(run_id))
    await task

    assert result.action == "deny"


@pytest.mark.asyncio
async def test_cancel_run_while_waiting() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default")

    async def waiter() -> ResolvedPermission:
        return await manager.wait_for_permission(_make_request(run_id))

    wait_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.01)
    await manager.cancel_run(run_id)
    result = await wait_task

    assert result.action == "deny"
    assert "cancel" in result.reason
    state = manager.get_run(run_id)
    assert state is not None
    assert state.status == "cancelled"


@pytest.mark.asyncio
async def test_duplicate_permission_resolve_returns_error_event() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default")
    request = _make_request(run_id)

    wait_task = asyncio.create_task(manager.wait_for_permission(request))
    await asyncio.sleep(0.01)

    first = await manager.resolve_permission(
        run_id=run_id,
        permission_request_id="perm_1",
        decision="allow",
    )
    second = await manager.resolve_permission(
        run_id=run_id,
        permission_request_id="perm_1",
        decision="allow",
    )
    result = await wait_task

    assert first is not None
    assert first.type == "permission_resolved"
    assert second is not None
    assert second.type == "error"
    assert result.action == "allow"


@pytest.mark.asyncio
async def test_unknown_run_id_resolve_returns_error() -> None:
    manager = RunManager()
    event = await manager.resolve_permission(
        run_id="run_missing",
        permission_request_id="perm_1",
        decision="allow",
    )
    assert event is not None
    assert event.type == "error"
    assert "unknown run_id" in event.payload["error"]


@pytest.mark.asyncio
async def test_record_event_updates_status() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default")
    await manager.record_event(
        permission_required_event(
            run_id=run_id,
            session_id="default",
            seq=1,
            request=_make_request(run_id),
        )
    )
    state = manager.get_run(run_id)
    assert state is not None
    assert state.status == "waiting_permission"


@pytest.mark.asyncio
async def test_wait_for_permission_registers_pending_before_emit() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default")
    seen_pending = False

    async def subscriber(event) -> None:
        nonlocal seen_pending
        if event.type != "permission_required":
            return
        state = manager.get_run(run_id)
        seen_pending = state is not None and state.pending is not None
        await manager.resolve_permission(
            run_id=run_id,
            permission_request_id="perm_1",
            decision="allow",
        )

    manager.subscribe(run_id, subscriber)
    result = await manager.wait_for_permission(_make_request(run_id))

    assert result.action == "allow"
    assert seen_pending is True


@pytest.mark.asyncio
async def test_session_event_history_is_trimmed(monkeypatch) -> None:
    monkeypatch.setenv("KGENT_SESSION_EVENT_MAX", "3")
    manager = RunManager()
    manager._session_event_max = 3
    run_id = manager.create_run(session_id="trim")
    for index in range(5):
        await manager.publish_session_event(
            AgentEvent(
                type="agent_step",
                run_id=run_id,
                session_id="trim",
                seq=index,
                payload={"index": index},
            )
        )
    history = manager.get_session_events_after("trim", 0)
    assert len(history) == 3
    assert history[0].payload["index"] == 2


@pytest.mark.asyncio
async def test_loop_checkpoint_stored_without_messages_in_history() -> None:
    from app.runtime.protocol import loop_checkpoint_event
    from app.runtime.messages import Message

    manager = RunManager()
    run_id = manager.create_run(session_id="slim")
    event = loop_checkpoint_event(
        run_id=run_id,
        session_id="slim",
        seq=1,
        checkpoint="before_model_call",
        turn_index=0,
        messages=[Message(role="user", content="hello")],
        tool_schemas=[{"name": "calculator"}],
    )
    await manager.publish_session_event(event)
    stored = manager.get_session_events_after("slim", 0)[0]
    assert "messages" not in stored.payload
    assert "tool_schemas" not in stored.payload
    assert stored.payload["checkpoint"] == "before_model_call"


@pytest.mark.asyncio
async def test_cancel_runs_for_connection_skips_completed_runs() -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="default", connection_id="conn_1")
    await manager.record_event(
        permission_required_event(
            run_id=run_id,
            session_id="default",
            seq=1,
            request=_make_request(run_id),
        )
    )
    await manager.record_event(
        permission_required_event(
            run_id=run_id,
            session_id="default",
            seq=2,
            request=_make_request(run_id, "perm_2"),
        ).model_copy(update={"type": "run_finished", "payload": {"answer": "ok"}})
    )

    await manager.cancel_runs_for_connection("conn_1")

    state = manager.get_run(run_id)
    assert state is not None
    assert state.status == "completed"


@pytest.mark.asyncio
async def test_execute_run_clears_active_run_when_failure_event_persistence_fails(monkeypatch) -> None:
    manager = RunManager()
    run_id = manager.create_run(session_id="persist_fail")

    class FailingPersistence:
        def append_agent_event(self, session_id, event) -> None:
            raise PersistenceError("transcript full")

    async def fail_run(**_kwargs) -> None:
        raise RunManagerError("initial persistence failure")

    monkeypatch.setattr(runtime_service, "run_agent_stream", fail_run)
    manager.set_persistence(FailingPersistence())  # type: ignore[arg-type]

    await runtime_service.execute_run(
        run_manager=manager,
        run_id=run_id,
        session_id="persist_fail",
        message="hello",
        model_client=object(),  # type: ignore[arg-type]
        tools=[],
        policy=object(),  # type: ignore[arg-type]
        max_steps=1,
        max_session_messages=10,
        project_root=Path.cwd(),
        persistence=None,
    )

    state = manager.get_run(run_id)
    assert state is not None
    assert state.status == "failed"
    assert manager.get_active_run_id("persist_fail") is None
