"""AgentHost implementations bridging the loop to external IO (V0.2.1)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from app.runtime.messages import AgentResult, AgentStep
from app.runtime.protocol import (
    AgentEvent,
    PermissionRequest,
    ResolvedPermission,
    agent_step_event,
    new_permission_request_id,
    permission_required_event,
    permission_resolved_event,
    utc_now,
)


class AgentHost(Protocol):
    async def emit(self, event: AgentEvent) -> None: ...

    async def request_permission(self, request: PermissionRequest) -> ResolvedPermission: ...

    async def check_cancelled(self) -> bool: ...


class NullHost:
    """No-op host for tests that do not care about events."""

    async def emit(self, event: AgentEvent) -> None:
        return None

    async def request_permission(self, request: PermissionRequest) -> ResolvedPermission:
        return ResolvedPermission(action="deny", reason="NullHost auto-denies ask")

    async def check_cancelled(self) -> bool:
        return False


class CollectingHost:
    """Collects events and steps; used by run_agent() test/helper wrapper."""

    def __init__(
        self,
        *,
        run_id: str,
        session_id: str,
        auto_resolve_ask: bool = False,
        default_ask_decision: ResolvedPermission | None = None,
    ) -> None:
        self.run_id = run_id
        self.session_id = session_id
        self.auto_resolve_ask = auto_resolve_ask
        self.default_ask_decision = default_ask_decision or ResolvedPermission(
            action="deny",
            reason="ask not supported in sync HTTP mode",
        )
        self.events: list[AgentEvent] = []
        self.steps: list[AgentStep] = []
        self.answer: str = ""
        self.message_count: int = 0
        self._seq = 0
        self._cancelled = False

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def emit(self, event: AgentEvent) -> None:
        self.events.append(event)
        if event.type == "agent_step":
            step_data = event.payload.get("step")
            if step_data:
                self.steps.append(AgentStep.model_validate(step_data))
        elif event.type == "run_finished":
            self.answer = str(event.payload.get("answer", ""))
            self.message_count = int(event.payload.get("message_count", 0))
            steps_payload = event.payload.get("steps")
            if isinstance(steps_payload, list):
                self.steps = [AgentStep.model_validate(item) for item in steps_payload]
        elif event.type == "run_cancelled":
            self._cancelled = True

    async def request_permission(self, request: PermissionRequest) -> ResolvedPermission:
        seq = self._next_seq()
        await self.emit(
            permission_required_event(
                run_id=self.run_id,
                session_id=self.session_id,
                seq=seq,
                request=request,
            )
        )
        if self.auto_resolve_ask:
            decision = self.default_ask_decision
        else:
            decision = self.default_ask_decision
        await self.emit(
            permission_resolved_event(
                run_id=self.run_id,
                session_id=self.session_id,
                seq=self._next_seq(),
                permission_request_id=request.permission_request_id,
                decision=decision.action,
            )
        )
        return decision

    async def check_cancelled(self) -> bool:
        return self._cancelled

    def to_agent_result(self) -> AgentResult:
        return AgentResult(
            answer=self.answer,
            steps=list(self.steps),
            session_id=self.session_id,
            message_count=self.message_count,
        )


EventSubscriber = Callable[[AgentEvent], Awaitable[None] | None]


class CLIHost:
    """Terminal host: prints steps and prompts [y/N] for permission."""

    def __init__(
        self,
        *,
        run_id: str,
        session_id: str,
        asker: Callable[[PermissionRequest], Awaitable[ResolvedPermission]] | None = None,
        on_step: Callable[[AgentStep], None] | None = None,
    ) -> None:
        self.run_id = run_id
        self.session_id = session_id
        self._asker = asker
        self._on_step = on_step
        self._seq = 0
        self._cancelled = False

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def emit(self, event: AgentEvent) -> None:
        if event.type == "agent_step" and self._on_step is not None:
            step_data = event.payload.get("step")
            if step_data:
                self._on_step(AgentStep.model_validate(step_data))

    async def request_permission(self, request: PermissionRequest) -> ResolvedPermission:
        if self._asker is not None:
            return await self._asker(request)
        return ResolvedPermission(action="deny", reason="no asker configured")

    async def check_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True


def build_permission_request(
    *,
    run_id: str,
    session_id: str,
    tool_use_id: str,
    tool_name: str,
    risk_level: str,
    tool_input: dict,
    reason: str | None = None,
) -> PermissionRequest:
    return PermissionRequest(
        permission_request_id=new_permission_request_id(),
        run_id=run_id,
        session_id=session_id,
        tool_use_id=tool_use_id,
        tool_name=tool_name,
        risk_level=risk_level,  # type: ignore[arg-type]
        tool_input=tool_input,
        reason=reason,
    )


def make_run_started_event(run_id: str, session_id: str) -> AgentEvent:
    return AgentEvent(
        type="run_started",
        run_id=run_id,
        session_id=session_id,
        seq=1,
        payload={},
        created_at=utc_now(),
    )
