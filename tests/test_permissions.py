"""V0.2 permission layer tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.runtime.loop import (
    PERMISSION_DENIED_PREFIX,
    _format_permission_denied,
    run_agent,
)
from app.runtime.messages import Message, ModelResponse, ToolUseBlock
from app.model_client import HeuristicModelClient
from app.runtime.permissions import (
    AllowAllPolicy,
    AskPolicy,
    InteractivePolicy,
    PermissionDecision,
    RiskBasedPolicy,
    build_policy,
    normalize_mode,
)
from app.api.chat import (
    build_api_policy,
    resolve_api_permission_mode,
)
from app.core.config import reload_settings
from app.main import app
from app.tools.base import tool_to_schema
from app.tools.calculator import CalculatorTool
from app.tools.list_files import ListFilesTool
from app.tools.read_file import ReadFileTool


# ---------------------------------------------------------------------------
# Tool metadata
# ---------------------------------------------------------------------------

def test_existing_tools_carry_risk_level() -> None:
    assert CalculatorTool.risk_level == "low"
    assert ListFilesTool.risk_level == "low"
    assert ReadFileTool.risk_level == "medium"


def test_tool_to_schema_does_not_leak_risk_level() -> None:
    schema = tool_to_schema(CalculatorTool())
    assert "risk_level" not in schema
    assert set(schema.keys()) == {"name", "description", "input_schema"}


# ---------------------------------------------------------------------------
# Policy unit tests
# ---------------------------------------------------------------------------

class _MockTool:
    name = "mock_danger"
    description = "test-only high-risk tool"
    risk_level = "high"
    input_schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    async def call(self, input: dict[str, Any]) -> str:  # pragma: no cover - never invoked
        raise AssertionError("mock high-risk tool must never execute")


def _make_tool_use(name: str = "calculator") -> ToolUseBlock:
    return ToolUseBlock(id="toolu_test", name=name, input={"expression": "1+1"})


@pytest.mark.asyncio
async def test_allow_all_policy_always_allows() -> None:
    policy = AllowAllPolicy()
    decision = await policy.decide(_MockTool(), _make_tool_use("mock_danger"))
    assert decision.action == "allow"


@pytest.mark.asyncio
async def test_risk_based_policy_allows_low_medium_denies_high() -> None:
    policy = RiskBasedPolicy()

    low = await policy.decide(CalculatorTool(), _make_tool_use("calculator"))
    medium = await policy.decide(ReadFileTool(project_root=Path.cwd()), _make_tool_use("read_file"))
    high = await policy.decide(_MockTool(), _make_tool_use("mock_danger"))

    assert low.action == "allow"
    assert medium.action == "allow"
    assert high.action == "deny"
    assert "high" in high.reason


@pytest.mark.asyncio
async def test_ask_policy_auto_allows_low_and_asks_medium() -> None:
    policy = AskPolicy()

    low_decision = await policy.decide(CalculatorTool(), _make_tool_use("calculator"))
    medium_decision = await policy.decide(ReadFileTool(project_root=Path.cwd()), _make_tool_use("read_file"))

    assert low_decision.action == "allow"
    assert medium_decision.action == "ask"
    assert "medium" in medium_decision.reason


@pytest.mark.asyncio
async def test_interactive_policy_auto_allows_low_and_defers_medium_to_asker() -> None:
    captured: list[tuple[str, str]] = []

    async def asker(tool, tool_use) -> bool:
        captured.append((tool.name, tool.risk_level))
        return False  # reject

    policy = InteractivePolicy(asker=asker)

    low_decision = await policy.decide(CalculatorTool(), _make_tool_use("calculator"))
    medium_decision = await policy.decide(ReadFileTool(project_root=Path.cwd()), _make_tool_use("read_file"))

    assert low_decision.action == "allow"
    assert captured == [("read_file", "medium")]
    assert medium_decision.action == "deny"
    assert medium_decision.reason == "user rejected"


@pytest.mark.asyncio
async def test_interactive_policy_approves_when_asker_returns_true() -> None:
    async def asker(_tool, _tool_use) -> bool:
        return True

    policy = InteractivePolicy(asker=asker)
    decision = await policy.decide(_MockTool(), _make_tool_use("mock_danger"))

    assert decision.action == "allow"
    assert decision.reason == "user approved"


def test_normalize_mode_falls_back_to_risk_based() -> None:
    assert normalize_mode("allow_all") == "allow_all"
    assert normalize_mode("risk-based") == "risk_based"
    assert normalize_mode("INTERACTIVE") == "interactive"
    assert normalize_mode(None) == "risk_based"
    assert normalize_mode("nonsense") == "risk_based"


def test_build_policy_requires_asker_for_interactive() -> None:
    with pytest.raises(ValueError):
        build_policy("interactive")


def test_permission_decided_helper_serializes_reason() -> None:
    assert _format_permission_denied("") == PERMISSION_DENIED_PREFIX
    assert _format_permission_denied("risk_level=high not in (low, medium)") == (
        f"{PERMISSION_DENIED_PREFIX}: risk_level=high not in (low, medium)"
    )


# ---------------------------------------------------------------------------
# End-to-end: deny path produces observe(is_error=True) + after_permission trace
# ---------------------------------------------------------------------------

class _ScriptedClient:
    """Emit a fixed tool_use on first call, then a final text answer."""

    def __init__(self, tool_use: ToolUseBlock, final_text: str = "已停止，工具被拒绝。"):
        self._tool_use = tool_use
        self._final_text = final_text
        self._turn = 0

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        self._turn += 1
        if self._turn == 1:
            return ModelResponse(
                assistant_message=Message(
                    role="assistant",
                    content=[self._tool_use],
                    assistant_text="我打算调用 mock_danger。",
                ),
                text="我打算调用 mock_danger。",
                tool_uses=[self._tool_use],
            )
        return ModelResponse(
            assistant_message=Message(role="assistant", content=self._final_text),
            text=self._final_text,
        )


@pytest.mark.asyncio
async def test_run_agent_denies_high_risk_and_emits_after_permission_trace() -> None:
    events: list[str] = []

    def tracer(event: str, _turn_index: int, _messages: list[Message], _added) -> None:
        events.append(event)

    tool_use = ToolUseBlock(id="toolu_x", name="mock_danger", input={})
    client = _ScriptedClient(tool_use)

    result = await run_agent(
        user_input="尝试调用 mock_danger",
        model_client=client,
        tools=[_MockTool()],
        max_steps=4,
        session_id="t_permissions_deny",
        on_trace=tracer,
        policy=RiskBasedPolicy(),
    )

    call_step = next(step for step in result.steps if step.type == "call")
    observe_step = next(step for step in result.steps if step.type == "observe")
    final_step = next(step for step in result.steps if step.type == "final")

    assert call_step.decision == "deny"
    assert observe_step.is_error is True
    assert observe_step.content.startswith(PERMISSION_DENIED_PREFIX)
    assert "high" in observe_step.content
    assert "after_permission" in events
    assert final_step.content == result.answer


@pytest.mark.asyncio
async def test_run_agent_default_policy_is_allow_all(tmp_path: Path) -> None:
    """Calling run_agent without a policy keeps V0.1 behaviour (everything allowed)."""
    from app.tools.registry import build_tools

    result = await run_agent(
        user_input="帮我算一下 12 * 8 + 6",
        model_client=HeuristicModelClient(),
        tools=build_tools(tmp_path),
        session_id="t_permissions_default_allow",
    )

    call = next(step for step in result.steps if step.type == "call")
    assert call.decision == "allow"
    assert "102" in result.answer


# ---------------------------------------------------------------------------
# API integration: interactive must be downgraded to risk_based on the HTTP side
# ---------------------------------------------------------------------------

def test_resolve_api_permission_mode_downgrades_interactive() -> None:
    assert resolve_api_permission_mode("interactive") == "risk_based"
    assert resolve_api_permission_mode("risk_based") == "risk_based"
    assert resolve_api_permission_mode("allow_all") == "allow_all"


def test_build_api_policy_never_returns_interactive() -> None:
    assert isinstance(build_api_policy("interactive"), RiskBasedPolicy)
    assert isinstance(build_api_policy("risk_based"), RiskBasedPolicy)
    assert isinstance(build_api_policy("allow_all"), AllowAllPolicy)


def test_health_exposes_permission_mode_and_tool_risks(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "interactive")
    reload_settings()

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["permission_mode"] == "interactive"
    assert data["effective_permission_mode"] == "risk_based"
    assert data["tool_risks"]["calculator"] == "low"
    assert data["tool_risks"]["read_file"] == "medium"


def test_permission_decision_pydantic_model() -> None:
    d = PermissionDecision(action="deny", reason="just because")
    assert d.action == "deny"
    assert d.reason == "just because"
    with pytest.raises(Exception):
        PermissionDecision(action="bogus")  # type: ignore[arg-type]
