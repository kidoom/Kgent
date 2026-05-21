"""Tests for RunManager (V0.2.1)."""

from __future__ import annotations

import asyncio

import pytest

from app.runtime.protocol import PermissionRequest, ResolvedPermission, permission_required_event
from app.runtime.run_manager import RunManager


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
