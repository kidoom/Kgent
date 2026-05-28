"""Tests for the subagent harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.memory.persistence import build_persistence_service
from app.memory.session_store import get_or_create_session, reset_sessions
from app.runtime.messages import AgentResult, Message, ModelResponse, ToolResultBlock, ToolUseBlock
from app.runtime.permissions import AllowAllPolicy
from app.runtime.subagent import (
    SubagentResult,
    generate_child_session_id,
    run_subagent,
)
from app.tools.base import tool_to_schema
from app.tools.registry import build_tools
from app.tools.task import DEFAULT_SUBAGENT_MAX_STEPS, TaskTool, _format_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SimpleModelClient:
    """Returns a fixed final answer on first call."""

    def __init__(self, answer: str = "subagent done") -> None:
        self.calls: list[tuple[list[Message], list[dict]]] = []
        self._answer = answer

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        self.calls.append((messages, tools))
        return ModelResponse(
            assistant_message=Message(role="assistant", content=self._answer),
            text=self._answer,
        )


class _ToolUsingModelClient:
    """First call returns a tool_use, second call returns final answer."""

    def __init__(self, tool_result_content: str = "file contents here") -> None:
        self._calls: list[tuple[list[Message], list[dict]]] = []
        self._tool_result = tool_result_content
        self._call_count = 0

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        self._calls.append((messages, tools))
        self._call_count += 1
        if self._call_count == 1:
            tu = ToolUseBlock(id="tu_child_1", name="read_file", input={"path": "test.py"})
            return ModelResponse(
                assistant_message=Message(
                    role="assistant",
                    content=[tu],
                    assistant_text="reading file",
                ),
                text="reading file",
                tool_uses=[tu],
            )
        return ModelResponse(
            assistant_message=Message(role="assistant", content="analysis complete"),
            text="analysis complete",
        )


class _MaxStepsModelClient:
    """Always returns tool_use to exhaust max steps."""

    def __init__(self) -> None:
        self._call_count = 0

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        self._call_count += 1
        tu = ToolUseBlock(id=f"tu_exhaust_{self._call_count}", name="read_file", input={"path": "x.py"})
        return ModelResponse(
            assistant_message=Message(
                role="assistant",
                content=[tu],
                assistant_text=f"step {self._call_count}",
            ),
            text=f"step {self._call_count}",
            tool_uses=[tu],
        )


# ---------------------------------------------------------------------------
# 4.1: Parent can delegate and receives child summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subagent_returns_summary(tmp_path: Path) -> None:
    client = _SimpleModelClient(answer="task completed successfully")

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    result = await run_subagent(
        prompt="analyze the project",
        parent_session_id="parent-1",
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
    )

    assert result.status == "completed"
    assert "task completed successfully" in result.summary
    assert result.child_session_id.startswith("sub_")
    assert result.child_session_id != "parent-1"


@pytest.mark.asyncio
async def test_task_tool_delegates_and_returns_summary(tmp_path: Path) -> None:
    client = _SimpleModelClient(answer="child summary here")

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    async def runner(prompt: str, max_steps: int | None = None):
        return await run_subagent(
            prompt=prompt,
            parent_session_id="parent-task",
            model_client=client,
            build_child_tools=build_child_tools,
            project_root=tmp_path,
            max_steps=max_steps or DEFAULT_SUBAGENT_MAX_STEPS,
        )

    task_tool = TaskTool(runner=runner)
    result = await task_tool.call({"prompt": "do something"})
    assert "child summary here" in result


# ---------------------------------------------------------------------------
# 4.2: Child requests don't include parent transcript
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_does_not_receive_parent_messages(tmp_path: Path) -> None:
    reset_sessions()
    client = _SimpleModelClient(answer="done")

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    # Populate parent session with messages.
    parent_sid = "parent-isolation"
    parent_msgs = get_or_create_session(parent_sid)
    parent_msgs.append(Message(role="user", content="parent question"))
    parent_msgs.append(Message(role="assistant", content="parent answer"))
    parent_msgs.append(Message(role="user", content="parent follow-up"))

    result = await run_subagent(
        prompt="child task prompt",
        parent_session_id=parent_sid,
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
    )

    assert result.status == "completed"
    # Verify child model call did not contain parent messages.
    child_messages = client.calls[0][0]
    child_contents = [m.content for m in child_messages if isinstance(m.content, str)]
    assert "parent question" not in child_contents
    assert "parent answer" not in child_contents
    assert "parent follow-up" not in child_contents


# ---------------------------------------------------------------------------
# 4.3: Child intermediate tool results not in parent session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_tool_results_not_in_parent_session(tmp_path: Path) -> None:
    reset_sessions()
    client = _ToolUsingModelClient()

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    parent_sid = "parent-no-leak"
    parent_msgs = get_or_create_session(parent_sid)
    parent_msgs.append(Message(role="user", content="parent msg"))

    result = await run_subagent(
        prompt="read and analyze",
        parent_session_id=parent_sid,
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
        max_steps=3,
    )

    assert result.status == "completed"
    # Parent session should only have the original message.
    assert len(parent_msgs) == 1
    assert parent_msgs[0].content == "parent msg"


# ---------------------------------------------------------------------------
# 4.4: Task tool absent from child tool schemas
# ---------------------------------------------------------------------------


def test_task_tool_absent_from_child_tools(tmp_path: Path) -> None:
    # Parent tools: include task tool.
    parent_tools = build_tools(tmp_path, include_task_tool=True, subagent_runner=lambda **kw: None)
    parent_names = [t.name for t in parent_tools]
    assert "task" in parent_names

    # Child tools: no task tool.
    child_tools = build_tools(tmp_path)
    child_names = [t.name for t in child_tools]
    assert "task" not in child_names

    # Child schemas also exclude task.
    child_schemas = [tool_to_schema(t) for t in child_tools]
    schema_names = [s["name"] for s in child_schemas]
    assert "task" not in schema_names


# ---------------------------------------------------------------------------
# 4.5: Max-step exhaustion returns clear error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_steps_exhaustion_returns_error(tmp_path: Path) -> None:
    client = _MaxStepsModelClient()

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    result = await run_subagent(
        prompt="keep going forever",
        parent_session_id="parent-max",
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
        max_steps=2,
    )

    assert result.status == "max_steps"
    assert "max" in result.summary.lower() or "stopped" in result.summary.lower()


def test_max_steps_format_result() -> None:
    result = SubagentResult(
        summary="ran out of steps",
        child_session_id="child-1",
        status="max_steps",
        error="max steps reached",
    )
    formatted = _format_result(result)
    assert "maximum steps" in formatted
    assert "ran out of steps" in formatted


def test_error_format_result() -> None:
    result = SubagentResult(
        summary="something broke",
        child_session_id="child-1",
        status="error",
        error="connection timeout",
    )
    formatted = _format_result(result)
    assert "Subagent error" in formatted
    assert "connection timeout" in formatted


# ---------------------------------------------------------------------------
# 4.6: Child transcript uses distinct child session id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_child_session_id_is_distinct(tmp_path: Path) -> None:
    client = _SimpleModelClient(answer="done")

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    result = await run_subagent(
        prompt="task",
        parent_session_id="parent-distinct",
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
    )

    assert result.child_session_id != "parent-distinct"
    assert result.child_session_id.startswith("sub_")


def test_generate_child_session_id_unique() -> None:
    ids = {generate_child_session_id("p") for _ in range(100)}
    assert len(ids) == 100  # All unique


@pytest.mark.asyncio
async def test_child_persistence_uses_child_session_id(tmp_path: Path) -> None:
    reset_sessions()
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=5_000_000,
    )
    client = _SimpleModelClient(answer="persisted")

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    result = await run_subagent(
        prompt="persist this",
        parent_session_id="parent-persist",
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
        persistence=persistence,
    )

    # Child transcript should exist under child session id.
    entries, _ = persistence.load_transcript(result.child_session_id)
    assert len(entries) > 0

    # Parent transcript should be empty (no child messages leaked).
    parent_entries, _ = persistence.load_transcript("parent-persist")
    assert len(parent_entries) == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_prompt_raises() -> None:
    async def runner(**kw):
        return SubagentResult(summary="x", child_session_id="c", status="completed")

    tool = TaskTool(runner=runner)
    with pytest.raises(ValueError, match="non-empty"):
        await tool.call({"prompt": ""})

    with pytest.raises(ValueError, match="non-empty"):
        await tool.call({})


def test_default_max_steps() -> None:
    assert DEFAULT_SUBAGENT_MAX_STEPS == 5


# ---------------------------------------------------------------------------
# SubagentHost
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subagent_host_drops_events() -> None:
    """Child emit() should be silently dropped, not forwarded to parent."""
    from app.runtime.host import CollectingHost, SubagentHost
    from app.runtime.protocol import agent_step_event
    from app.runtime.messages import AgentStep

    parent = CollectingHost(run_id="run_parent", session_id="sess_parent")
    child_host = SubagentHost(parent, parent_run_id="run_parent", parent_session_id="sess_parent")

    event = agent_step_event(
        run_id="run_child",
        session_id="sess_child",
        seq=1,
        step=AgentStep(type="think", turn_index=0, content="hi"),
    )
    await child_host.emit(event)

    # Parent should NOT have received the child event.
    assert len(parent.events) == 0


@pytest.mark.asyncio
async def test_subagent_host_forwards_permission_with_parent_ids() -> None:
    """Permission requests should be re-written with parent run/session ids."""
    from app.runtime.host import CollectingHost, SubagentHost, build_permission_request

    parent = CollectingHost(run_id="run_parent", session_id="sess_parent")
    child_host = SubagentHost(parent, parent_run_id="run_parent", parent_session_id="sess_parent")

    request = build_permission_request(
        run_id="run_child",
        session_id="sess_child",
        tool_use_id="tu_1",
        tool_name="write_file",
        risk_level="medium",
        tool_input={"path": "x.txt", "content": "data"},
    )
    result = await child_host.request_permission(request)

    # Parent should have emitted permission_required and permission_resolved events.
    assert len(parent.events) == 2
    assert parent.events[0].type == "permission_required"
    assert parent.events[1].type == "permission_resolved"
    # The events should carry the PARENT's run_id, not the child's.
    assert parent.events[0].run_id == "run_parent"
    assert parent.events[0].session_id == "sess_parent"
    # Result should be the parent's default decision.
    assert result.action == "deny"


@pytest.mark.asyncio
async def test_subagent_host_delegates_cancel_check() -> None:
    """check_cancelled() should delegate to the parent host."""
    from app.runtime.host import CollectingHost, SubagentHost

    parent = CollectingHost(run_id="run_parent", session_id="sess_parent")
    child_host = SubagentHost(parent, parent_run_id="run_parent", parent_session_id="sess_parent")

    assert await child_host.check_cancelled() is False
    parent._cancelled = True
    assert await child_host.check_cancelled() is True


@pytest.mark.asyncio
async def test_subagent_wraps_host_automatically(tmp_path: Path) -> None:
    """run_subagent should wrap a parent host with SubagentHost."""
    from app.runtime.host import CollectingHost

    parent = CollectingHost(run_id="run_parent", session_id="sess_parent")
    client = _SimpleModelClient(answer="wrapped")

    def build_child_tools(child_session_id: str):
        return build_tools(tmp_path, session_id=child_session_id)

    result = await run_subagent(
        prompt="test wrap",
        parent_session_id="parent-wrap",
        model_client=client,
        build_child_tools=build_child_tools,
        project_root=tmp_path,
        host=parent,
    )

    assert result.status == "completed"
    # The parent CollectingHost should NOT have received child events
    # (run_started, agent_step, run_finished are all dropped by SubagentHost).
    assert len(parent.events) == 0
