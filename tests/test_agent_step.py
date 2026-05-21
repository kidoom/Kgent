import pytest
from pydantic import ValidationError

from app.runtime.messages import AgentStep


def test_agent_step_serialization_roundtrip() -> None:
    step = AgentStep(
        type="call",
        turn_index=0,
        tool_use_id="toolu_abc",
        tool_name="calculator",
        tool_input={"expression": "1+1"},
    )
    data = step.model_dump()
    restored = AgentStep.model_validate(data)
    assert restored == step


def test_agent_step_think_requires_content() -> None:
    with pytest.raises(ValidationError):
        AgentStep(type="think", turn_index=0, content="   ")


def test_agent_step_call_requires_tool_fields() -> None:
    with pytest.raises(ValidationError):
        AgentStep(type="call", turn_index=0, tool_name="calculator", tool_input={})


def test_agent_step_observe_requires_content() -> None:
    with pytest.raises(ValidationError):
        AgentStep(
            type="observe",
            turn_index=0,
            tool_use_id="toolu_1",
            tool_name="calculator",
        )


def test_agent_step_decision_allowed_on_call_step() -> None:
    step = AgentStep(
        type="call",
        turn_index=1,
        tool_use_id="toolu_x",
        tool_name="calculator",
        tool_input={"expression": "1+1"},
        decision="deny",
    )
    assert step.decision == "deny"


def test_agent_step_decision_rejected_on_non_call_step() -> None:
    with pytest.raises(ValidationError):
        AgentStep(type="think", turn_index=0, content="planning", decision="allow")


def test_agent_step_decision_invalid_value() -> None:
    with pytest.raises(ValidationError):
        AgentStep(
            type="call",
            turn_index=0,
            tool_use_id="toolu_x",
            tool_name="calculator",
            tool_input={},
            decision="maybe",  # type: ignore[arg-type]
        )
