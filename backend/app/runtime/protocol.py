"""Runtime event / command / permission protocol (V0.2.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.runtime.messages import AgentStep

AgentEventType = Literal[
    "run_started",
    "agent_step",
    "tool_call_started",
    "permission_required",
    "permission_resolved",
    "tool_result",
    "run_finished",
    "run_failed",
    "run_cancelled",
    "error",
]

RunStatus = Literal[
    "running",
    "waiting_permission",
    "completed",
    "failed",
    "cancelled",
]

UserPermissionAction = Literal["allow", "deny"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_run_id() -> str:
    return f"run_{uuid4().hex[:12]}"


def new_permission_request_id() -> str:
    return f"perm_{uuid4().hex[:12]}"


class AgentEvent(BaseModel):
    type: AgentEventType
    run_id: str
    session_id: str
    seq: int
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class PermissionRequest(BaseModel):
    permission_request_id: str
    run_id: str
    session_id: str
    tool_use_id: str
    tool_name: str
    risk_level: Literal["low", "medium", "high"]
    tool_input: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class ResolvedPermission(BaseModel):
    """User-side permission resolution (allow/deny only)."""

    action: UserPermissionAction
    reason: str = ""


class StartRunCommand(BaseModel):
    type: Literal["start_run"] = "start_run"
    session_id: str = "default"
    message: str = Field(min_length=1)


class PermissionDecisionCommand(BaseModel):
    type: Literal["permission_decision"] = "permission_decision"
    run_id: str
    permission_request_id: str
    decision: UserPermissionAction
    remember: bool = False


class CancelRunCommand(BaseModel):
    type: Literal["cancel_run"] = "cancel_run"
    run_id: str


RuntimeCommand = StartRunCommand | PermissionDecisionCommand | CancelRunCommand


def agent_step_event(
    *,
    run_id: str,
    session_id: str,
    seq: int,
    step: AgentStep,
) -> AgentEvent:
    return AgentEvent(
        type="agent_step",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={"step": step.model_dump(mode="json")},
    )


def permission_required_event(
    *,
    run_id: str,
    session_id: str,
    seq: int,
    request: PermissionRequest,
) -> AgentEvent:
    return AgentEvent(
        type="permission_required",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={"permission_request": request.model_dump(mode="json")},
    )


def permission_resolved_event(
    *,
    run_id: str,
    session_id: str,
    seq: int,
    permission_request_id: str,
    decision: UserPermissionAction,
) -> AgentEvent:
    return AgentEvent(
        type="permission_resolved",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={
            "permission_request_id": permission_request_id,
            "decision": decision,
        },
    )


def tool_call_started_event(
    *,
    run_id: str,
    session_id: str,
    seq: int,
    tool_use_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
) -> AgentEvent:
    return AgentEvent(
        type="tool_call_started",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={
            "tool_use_id": tool_use_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
        },
    )


def run_finished_event(
    *,
    run_id: str,
    session_id: str,
    seq: int,
    answer: str,
    message_count: int,
    steps: list[AgentStep],
) -> AgentEvent:
    return AgentEvent(
        type="run_finished",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={
            "answer": answer,
            "message_count": message_count,
            "steps": [step.model_dump(mode="json") for step in steps],
        },
    )


def error_event(
    *,
    run_id: str,
    session_id: str,
    seq: int,
    error: str,
) -> AgentEvent:
    return AgentEvent(
        type="error",
        run_id=run_id,
        session_id=session_id,
        seq=seq,
        payload={"error": error},
    )
