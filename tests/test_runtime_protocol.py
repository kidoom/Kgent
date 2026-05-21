"""Tests for runtime protocol models (V0.2.1)."""

from app.runtime.messages import AgentStep
from app.runtime.protocol import (
    AgentEvent,
    CancelRunCommand,
    PermissionDecisionCommand,
    PermissionRequest,
    ResolvedPermission,
    StartRunCommand,
    agent_step_event,
    permission_required_event,
    tool_call_started_event,
)


def test_start_run_command_defaults() -> None:
    cmd = StartRunCommand(message="hello")
    assert cmd.type == "start_run"
    assert cmd.session_id == "default"
    assert cmd.message == "hello"


def test_permission_decision_command() -> None:
    cmd = PermissionDecisionCommand(
        run_id="run_1",
        permission_request_id="perm_1",
        decision="allow",
    )
    assert cmd.decision == "allow"
    assert cmd.remember is False


def test_cancel_run_command() -> None:
    cmd = CancelRunCommand(run_id="run_1")
    assert cmd.type == "cancel_run"


def test_agent_event_serialization() -> None:
    step = AgentStep(type="think", turn_index=0, content="planning")
    event = agent_step_event(
        run_id="run_1",
        session_id="default",
        seq=2,
        step=step,
    )
    data = event.model_dump(mode="json")
    assert data["type"] == "agent_step"
    assert data["run_id"] == "run_1"
    assert data["payload"]["step"]["type"] == "think"


def test_permission_request_and_resolved() -> None:
    req = PermissionRequest(
        permission_request_id="perm_x",
        run_id="run_x",
        session_id="default",
        tool_use_id="toolu_1",
        tool_name="read_file",
        risk_level="medium",
        tool_input={"path": "README.md"},
    )
    event = permission_required_event(
        run_id="run_x",
        session_id="default",
        seq=3,
        request=req,
    )
    assert event.type == "permission_required"
    assert event.payload["permission_request"]["tool_name"] == "read_file"

    resolved = ResolvedPermission(action="deny", reason="user rejected")
    assert resolved.action == "deny"


def test_agent_event_types() -> None:
    event = AgentEvent(
        type="run_started",
        run_id="run_1",
        session_id="s1",
        seq=1,
        payload={},
    )
    assert event.type == "run_started"


def test_tool_call_started_event() -> None:
    event = tool_call_started_event(
        run_id="run_1",
        session_id="s1",
        seq=3,
        tool_use_id="toolu_1",
        tool_name="read_file",
        tool_input={"path": "README.md"},
    )
    data = event.model_dump(mode="json")
    assert data["type"] == "tool_call_started"
    assert data["payload"]["tool_name"] == "read_file"
