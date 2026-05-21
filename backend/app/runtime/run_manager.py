"""Process-local run supervisor for interactive runtime (V0.2.1)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.runtime.protocol import (
    AgentEvent,
    PermissionRequest,
    ResolvedPermission,
    RunStatus,
    UserPermissionAction,
    error_event,
    new_run_id,
    permission_required_event,
    permission_resolved_event,
    utc_now,
)

EventSubscriber = Callable[[AgentEvent], Awaitable[None] | None]
ACTIVE_STATUSES: tuple[RunStatus, ...] = ("running", "waiting_permission")


class RunManagerError(Exception):
    pass


@dataclass
class PendingPermission:
    permission_request_id: str
    future: asyncio.Future[ResolvedPermission]


@dataclass
class RunState:
    run_id: str
    session_id: str
    status: RunStatus = "running"
    events: list[AgentEvent] = field(default_factory=list)
    seq: int = 0
    pending: PendingPermission | None = None
    connection_id: str | None = None
    error: str | None = None


class RunManager:
    """In-memory supervisor: one pending permission per run."""

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}
        self._connection_runs: dict[str, set[str]] = {}
        self._subscribers: dict[str, list[EventSubscriber]] = {}

    def create_run(
        self,
        *,
        session_id: str,
        connection_id: str | None = None,
        run_id: str | None = None,
    ) -> str:
        rid = run_id or new_run_id()
        self._runs[rid] = RunState(
            run_id=rid,
            session_id=session_id,
            connection_id=connection_id,
        )
        if connection_id:
            self._connection_runs.setdefault(connection_id, set()).add(rid)
        return rid

    def get_run(self, run_id: str) -> RunState | None:
        return self._runs.get(run_id)

    def is_cancelled(self, run_id: str) -> bool:
        state = self._runs.get(run_id)
        return state is not None and state.status == "cancelled"

    def subscribe(self, run_id: str, subscriber: EventSubscriber) -> None:
        self._subscribers.setdefault(run_id, []).append(subscriber)

    def _discard_connection_run(self, state: RunState) -> None:
        if not state.connection_id:
            return
        run_ids = self._connection_runs.get(state.connection_id)
        if run_ids is None:
            return
        run_ids.discard(state.run_id)
        if not run_ids:
            self._connection_runs.pop(state.connection_id, None)

    async def record_event(self, event: AgentEvent) -> None:
        state = self._runs.get(event.run_id)
        if state is None:
            return
        state.events.append(event)
        state.seq = max(state.seq, event.seq)
        if event.type == "run_finished":
            state.status = "completed"
            self._discard_connection_run(state)
        elif event.type == "run_failed":
            state.status = "failed"
            state.error = str(event.payload.get("error", ""))
            self._discard_connection_run(state)
        elif event.type == "run_cancelled":
            state.status = "cancelled"
            self._discard_connection_run(state)
        elif event.type == "permission_required":
            state.status = "waiting_permission"
        elif event.type == "permission_resolved" and state.status == "waiting_permission":
            state.status = "running"
        for subscriber in self._subscribers.get(event.run_id, []):
            result = subscriber(event)
            if asyncio.iscoroutine(result):
                await result

    async def wait_for_permission(self, request: PermissionRequest) -> ResolvedPermission:
        state = self._runs.get(request.run_id)
        if state is None:
            raise RunManagerError(f"unknown run_id: {request.run_id}")
        if state.status == "cancelled":
            return ResolvedPermission(action="deny", reason="run cancelled")
        if state.pending is not None:
            raise RunManagerError("run already has a pending permission request")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[ResolvedPermission] = loop.create_future()
        seq = state.seq + 1
        state.pending = PendingPermission(
            permission_request_id=request.permission_request_id,
            future=future,
        )
        state.status = "waiting_permission"
        await self.record_event(
            permission_required_event(
                run_id=request.run_id,
                session_id=request.session_id,
                seq=seq,
                request=request,
            )
        )

        try:
            return await future
        finally:
            if state.pending and state.pending.permission_request_id == request.permission_request_id:
                state.pending = None
            if state.status == "waiting_permission":
                state.status = "running"

    async def resolve_permission(
        self,
        *,
        run_id: str,
        permission_request_id: str,
        decision: UserPermissionAction,
    ) -> AgentEvent | None:
        state = self._runs.get(run_id)
        if state is None:
            return error_event(
                run_id=run_id,
                session_id="",
                seq=1,
                error=f"unknown run_id: {run_id}",
            )
        pending = state.pending
        if pending is None or pending.permission_request_id != permission_request_id:
            return error_event(
                run_id=run_id,
                session_id=state.session_id,
                seq=state.seq + 1,
                error=f"unknown or stale permission_request_id: {permission_request_id}",
            )
        if pending.future.done():
            return error_event(
                run_id=run_id,
                session_id=state.session_id,
                seq=state.seq + 1,
                error=f"permission_request_id already resolved: {permission_request_id}",
            )

        resolved = ResolvedPermission(
            action=decision,
            reason="user approved" if decision == "allow" else "user rejected",
        )
        pending.future.set_result(resolved)
        state.pending = None
        state.status = "running"

        event = permission_resolved_event(
            run_id=run_id,
            session_id=state.session_id,
            seq=state.seq + 1,
            permission_request_id=permission_request_id,
            decision=decision,
        )
        await self.record_event(event)
        return event

    async def cancel_run(self, run_id: str) -> AgentEvent | None:
        state = self._runs.get(run_id)
        if state is None:
            return error_event(
                run_id=run_id,
                session_id="",
                seq=1,
                error=f"unknown run_id: {run_id}",
            )
        if state.status not in ACTIVE_STATUSES:
            return None
        state.status = "cancelled"
        if state.pending and not state.pending.future.done():
            state.pending.future.set_result(
                ResolvedPermission(action="deny", reason="run cancelled")
            )
            state.pending = None

        event = AgentEvent(
            type="run_cancelled",
            run_id=run_id,
            session_id=state.session_id,
            seq=state.seq + 1,
            payload={},
            created_at=utc_now(),
        )
        await self.record_event(event)
        return event

    async def cancel_runs_for_connection(self, connection_id: str) -> None:
        run_ids = list(self._connection_runs.get(connection_id, set()))
        for run_id in run_ids:
            state = self._runs.get(run_id)
            if state is not None and state.status in ACTIVE_STATUSES:
                await self.cancel_run(run_id)
        self._connection_runs.pop(connection_id, None)

    def reset(self) -> None:
        """Clear all runs (for tests)."""
        for state in self._runs.values():
            if state.pending and not state.pending.future.done():
                state.pending.future.set_result(
                    ResolvedPermission(action="deny", reason="run manager reset")
                )
        self._runs.clear()
        self._connection_runs.clear()
        self._subscribers.clear()


class RunManagerHost:
    """Host backed by RunManager for WebSocket / supervised runs."""

    def __init__(self, run_manager: RunManager, run_id: str, session_id: str) -> None:
        self._run_manager = run_manager
        self.run_id = run_id
        self.session_id = session_id

    async def emit(self, event: AgentEvent) -> None:
        await self._run_manager.record_event(event)

    async def request_permission(self, request: PermissionRequest) -> ResolvedPermission:
        return await self._run_manager.wait_for_permission(request)

    async def check_cancelled(self) -> bool:
        return self._run_manager.is_cancelled(self.run_id)
