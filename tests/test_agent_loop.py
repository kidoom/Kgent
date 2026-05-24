from pathlib import Path
from typing import Any

import pytest

from app.memory.session_store import get_or_create_session
from app.runtime.loop import run_agent
from app.runtime.messages import Message, ModelResponse, ToolResultBlock, ToolUseBlock
from app.runtime.permissions import AllowAllPolicy, RiskBasedPolicy
from app.tools.registry import build_tools
from fake_model import FakeModelClient




class CapturingTextModelClient:
    def __init__(self):
        self.calls: list[list[Message]] = []

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        self.calls.append(messages)
        text = "captured"
        return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

class SingleToolModelClient:
    def __init__(self, tool_use: ToolUseBlock):
        self.tool_use = tool_use

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        pending = _latest_pending_tool_result(messages)
        if pending is not None:
            text = f"tool result: {pending.content}"
            return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

        plan = f"calling {self.tool_use.name}"
        return ModelResponse(
            assistant_message=Message(
                role="assistant",
                content=[self.tool_use],
                assistant_text=plan,
            ),
            text=plan,
            tool_uses=[self.tool_use],
        )


def _latest_pending_tool_result(messages: list[Message]) -> ToolResultBlock | None:
    last_index = -1
    last_block: ToolResultBlock | None = None
    for index, message in enumerate(messages):
        if message.role != "user" or not isinstance(message.content, list):
            continue
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                last_index = index
                last_block = block
    if last_block is None:
        return None
    for message in messages[last_index + 1 :]:
        if message.role == "assistant":
            return None
    return last_block


@pytest.mark.asyncio
async def test_agent_pure_text_think_then_final() -> None:
    result = await run_agent(
        user_input="introduce yourself",
        model_client=FakeModelClient(),
        tools=build_tools(Path.cwd()),
        session_id="test-pure-text",
    )

    assert [step.type for step in result.steps] == ["think", "final"]
    assert result.steps[-1].content == result.answer


@pytest.mark.asyncio
async def test_agent_calculator_tool(tmp_path: Path) -> None:
    result = await run_agent(
        user_input="please calculate 12 * 8 + 6",
        model_client=FakeModelClient(),
        tools=build_tools(tmp_path),
        session_id="test-calculator",
    )

    assert "102" in result.answer
    assert [step.type for step in result.steps] == [
        "think",
        "call",
        "observe",
        "think",
        "final",
    ]
    assert result.steps[1].tool_name == "calculator"
    assert result.steps[2].is_error is False


@pytest.mark.asyncio
async def test_agent_read_file_tool(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nA tiny project.", encoding="utf-8")

    result = await run_agent(
        user_input="read README.md and summarize it",
        model_client=FakeModelClient(),
        tools=build_tools(tmp_path),
        session_id="test-read-file",
    )

    assert "Demo" in result.answer
    assert result.steps[1].type == "call"
    assert result.steps[1].tool_name == "read_file"
    assert result.steps[2].type == "observe"
    assert result.steps[2].is_error is False


@pytest.mark.asyncio
async def test_agent_tool_error_observe(tmp_path: Path) -> None:
    result = await run_agent(
        user_input="read missing.txt and summarize it",
        model_client=FakeModelClient(),
        tools=build_tools(tmp_path),
        session_id="test-tool-error",
    )

    observe = next(step for step in result.steps if step.type == "observe")
    assert observe.is_error is True
    assert result.steps[-1].type == "final"


@pytest.mark.asyncio
async def test_agent_write_file_allow_all_writes_file(tmp_path: Path) -> None:
    tool_use = ToolUseBlock(
        id="toolu_write_allow",
        name="write_file",
        input={"path": "notes.txt", "content": "hello from agent"},
    )

    result = await run_agent(
        user_input="write notes",
        model_client=SingleToolModelClient(tool_use),
        tools=build_tools(tmp_path),
        policy=AllowAllPolicy(),
        session_id="test-write-allow",
    )

    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello from agent"
    call = next(step for step in result.steps if step.type == "call")
    observe = next(step for step in result.steps if step.type == "observe")
    assert call.tool_name == "write_file"
    assert call.decision == "allow"
    assert observe.is_error is False
    assert "written: notes.txt" in observe.content


@pytest.mark.asyncio
async def test_agent_write_file_risk_based_denies_without_mutation(tmp_path: Path) -> None:
    tool_use = ToolUseBlock(
        id="toolu_write_deny",
        name="write_file",
        input={"path": "notes.txt", "content": "should not be written"},
    )

    result = await run_agent(
        user_input="write notes",
        model_client=SingleToolModelClient(tool_use),
        tools=build_tools(tmp_path),
        policy=RiskBasedPolicy(),
        session_id="test-write-deny",
    )

    assert not (tmp_path / "notes.txt").exists()
    call = next(step for step in result.steps if step.type == "call")
    observe = next(step for step in result.steps if step.type == "observe")
    assert call.tool_name == "write_file"
    assert call.decision == "deny"
    assert observe.is_error is True
    assert observe.content.startswith("permission_denied:")


@pytest.mark.asyncio
async def test_agent_edit_file_allow_all_edits_file(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("hello old world", encoding="utf-8")
    tool_use = ToolUseBlock(
        id="toolu_edit_allow",
        name="edit_file",
        input={"path": "README.md", "old_text": "old", "new_text": "new"},
    )

    result = await run_agent(
        user_input="edit readme",
        model_client=SingleToolModelClient(tool_use),
        tools=build_tools(tmp_path),
        policy=AllowAllPolicy(),
        session_id="test-edit-allow",
    )

    assert target.read_text(encoding="utf-8") == "hello new world"
    observe = next(step for step in result.steps if step.type == "observe")
    assert observe.is_error is False
    assert "edited: README.md" in observe.content


@pytest.mark.asyncio
async def test_agent_edit_file_risk_based_denies_without_mutation(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("hello old world", encoding="utf-8")
    tool_use = ToolUseBlock(
        id="toolu_edit_deny",
        name="edit_file",
        input={"path": "README.md", "old_text": "old", "new_text": "new"},
    )

    result = await run_agent(
        user_input="edit readme",
        model_client=SingleToolModelClient(tool_use),
        tools=build_tools(tmp_path),
        policy=RiskBasedPolicy(),
        session_id="test-edit-deny",
    )

    assert target.read_text(encoding="utf-8") == "hello old world"
    call = next(step for step in result.steps if step.type == "call")
    observe = next(step for step in result.steps if step.type == "observe")
    assert call.tool_name == "edit_file"
    assert call.decision == "deny"
    assert observe.is_error is True
    assert observe.content.startswith("permission_denied:")


@pytest.mark.asyncio
async def test_agent_context_builder_is_request_only(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("Use project context.", encoding="utf-8")
    model = CapturingTextModelClient()

    result = await run_agent(
        user_input="hello",
        model_client=model,
        tools=build_tools(tmp_path),
        session_id="test-context-builder",
        project_root=tmp_path,
    )

    assert result.answer == "captured"
    assert model.calls
    request_messages = model.calls[0]
    assert request_messages[0].role == "system"
    assert any(message.is_meta for message in request_messages)
    assert any("Use project context." in str(message.content) for message in request_messages if message.is_meta)

    session_messages = get_or_create_session("test-context-builder")
    assert all(message.role != "system" for message in session_messages)
    assert all(message.is_meta is False for message in session_messages)
    assert [message.role for message in session_messages] == ["user", "assistant"]