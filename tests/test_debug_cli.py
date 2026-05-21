from pathlib import Path

import pytest

from app.cli.debug import _make_tracer, _run_turn
from app.memory.session_store import reset_sessions
from app.runtime.permissions import RiskBasedPolicy
from app.tools.registry import build_tools
from fake_model import FakeModelClient


@pytest.mark.asyncio
async def test_debug_cli_one_shot_calculator(capsys, tmp_path: Path) -> None:
    reset_sessions()
    client = FakeModelClient()
    tools = build_tools(tmp_path)
    tracer = _make_tracer(show_system=False, compact=False)

    await _run_turn(
        user_input="帮我算一下 12 * 8 + 6",
        model_client=client,
        tools=tools,
        step_limit=8,
        session_id="debug-test",
        max_session_messages=100,
        trace=True,
        tracer=tracer,
        policy=RiskBasedPolicy(),
    )

    out = capsys.readouterr().out
    assert "CHECKPOINT" in out
    assert "messages (len=" in out
    assert "[call]" in out
    assert "[observe]" in out
    assert "calculator" in out
    assert "102" in out


@pytest.mark.asyncio
async def test_debug_cli_permission_flag_advertises_mode(capsys, tmp_path: Path) -> None:
    reset_sessions()
    client = FakeModelClient()
    tools = build_tools(tmp_path)
    tracer = _make_tracer(show_system=False, compact=True)

    await _run_turn(
        user_input="帮我算一下 12 * 8 + 6",
        model_client=client,
        tools=tools,
        step_limit=8,
        session_id="debug-test-perm",
        max_session_messages=100,
        trace=True,
        tracer=tracer,
        policy=RiskBasedPolicy(),
    )

    out = capsys.readouterr().out
    assert "decision=allow" in out
