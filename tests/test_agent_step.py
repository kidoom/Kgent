import pytest
from pydantic import ValidationError

from app.agent.messages import AgentStep


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
