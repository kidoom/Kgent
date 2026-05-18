from pathlib import Path

import pytest

from app.agent.loop import run_agent
from app.agent.model_client import HeuristicModelClient
from app.tools.registry import build_tools


@pytest.mark.asyncio
async def test_agent_calculator_tool(tmp_path: Path) -> None:
    result = await run_agent(
        user_input="帮我算一下 12 * 8 + 6",
        model_client=HeuristicModelClient(),
        tools=build_tools(tmp_path),
    )

    assert "102" in result.answer
    assert [step.type for step in result.steps] == ["tool_use", "tool_result"]
    assert result.steps[0].name == "calculator"


@pytest.mark.asyncio
async def test_agent_read_file_tool(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nA tiny project.", encoding="utf-8")

    result = await run_agent(
        user_input="请读取 README.md 并总结这个项目",
        model_client=HeuristicModelClient(),
        tools=build_tools(tmp_path),
    )

    assert "Demo" in result.answer
    assert result.steps[0].name == "read_file"
    assert result.steps[1].is_error is False
