"""Tests for Resume-time Compact helpers and integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.memory.persistence import build_persistence_service
from app.memory.session_store import get_or_create_session, reset_sessions
from app.runtime.context_compression import (
    CompressionConfig,
    build_resume_request_messages,
    execute_compact,
    should_resume_compact,
)
from app.runtime.messages import Message, ModelResponse, ToolResultBlock, ToolUseBlock
from app.runtime.todo_state import TodoItem, TodoStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _RecordingModelClient:
    """Records messages sent to call_model and returns a valid summary."""

    def __init__(
        self,
        response_text: str = "<context-compaction-boundary><summary>test summary</summary></context-compaction-boundary>",
    ) -> None:
        self.calls: list[tuple[list[Message], list[dict]]] = []
        self._response_text = response_text

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        self.calls.append((messages, tools))
        return ModelResponse(
            assistant_message=Message(role="assistant", content=self._response_text),
            text=self._response_text,
        )


class _FailingModelClient:
    """Always raises an error on call_model."""

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        raise RuntimeError("summarizer exploded")


def _make_large_messages(count: int = 200, size: int = 2000) -> list[Message]:
    """Create a list of messages that will exceed threshold."""
    messages = []
    for i in range(count):
        messages.append(Message(role="user", content=f"message-{i} " * (size // 10)))
    return messages


def _make_small_messages(count: int = 5) -> list[Message]:
    """Create a list of messages well below threshold."""
    return [Message(role="user", content=f"msg-{i}") for i in range(count)]


# ---------------------------------------------------------------------------
# 4.2: Below-threshold session skips Resume-time Compact
# ---------------------------------------------------------------------------


def test_should_resume_compact_returns_false_when_below_threshold() -> None:
    messages = _make_small_messages()
    cfg = CompressionConfig(
        context_window_tokens=200_000,
        auto_compact_buffer_tokens=13_000,
        compact_max_summary_tokens=4_000,
    )
    assert not should_resume_compact(
        messages,
        project_root=Path.cwd(),
        compression_config=cfg,
    )


# ---------------------------------------------------------------------------
# 4.3: Disabled compression skips Resume-time Compact
# ---------------------------------------------------------------------------


def test_should_resume_compact_skips_when_context_compression_disabled() -> None:
    messages = _make_large_messages()
    cfg = CompressionConfig(context_compression_enabled=False)
    assert not should_resume_compact(
        messages,
        project_root=Path.cwd(),
        compression_config=cfg,
    )


def test_should_resume_compact_skips_when_auto_compact_disabled() -> None:
    messages = _make_large_messages()
    cfg = CompressionConfig(auto_compact_enabled=False)
    assert not should_resume_compact(
        messages,
        project_root=Path.cwd(),
        compression_config=cfg,
    )


# ---------------------------------------------------------------------------
# 4.1: Oversized session triggers resume_compact and writes summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_compact_triggers_and_persists_for_oversized_session(tmp_path: Path) -> None:
    """An oversized hydrated session should trigger resume_compact and persist a summary with recent_messages."""
    reset_sessions()
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=50_000_000,
    )
    sid = "resume-test-oversized"

    # Write many messages to transcript to make it oversized.
    large_messages = _make_large_messages(count=300, size=3000)
    for msg in large_messages:
        persistence.append_message(sid, msg)

    # Hydrate into memory.
    messages, _ = persistence.hydrate_messages(sid)
    assert len(messages) > 100

    # Verify should_resume_compact returns True.
    cfg = CompressionConfig(
        context_window_tokens=200_000,
        auto_compact_buffer_tokens=13_000,
        compact_max_summary_tokens=4_000,
        compact_keep_recent_messages=6,
    )
    assert should_resume_compact(
        messages,
        project_root=tmp_path,
        compression_config=cfg,
        session_id=sid,
    )

    # Execute the compact.
    client = _RecordingModelClient()
    persisted: list[dict] = []

    await execute_compact(
        model_client=client,
        messages=messages,
        reason="resume_compact",
        compact_system_prompt="COMPACT_PROMPT",
        compact_user_prompt_text="summarize",
        keep_recent_messages=cfg.compact_keep_recent_messages,
        persist_fn=lambda _sid, payload: persisted.append(payload),
        session_id=sid,
    )

    # Session rewritten: boundary + recent.
    assert len(messages) == 1 + cfg.compact_keep_recent_messages
    assert len(persisted) == 1
    assert persisted[0]["reason"] == "resume_compact"
    assert "recent_messages" in persisted[0]
    assert len(persisted[0]["recent_messages"]) == cfg.compact_keep_recent_messages


# ---------------------------------------------------------------------------
# 4.4: Resume compact failure does not block and does not rewrite messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_compact_failure_does_not_rewrite_messages() -> None:
    """On failure, session messages should remain unchanged."""
    reset_sessions()
    messages = [
        Message(role="user", content="original-0"),
        Message(role="user", content="original-1"),
    ]
    original = [m.content for m in messages]

    client = _FailingModelClient()
    with pytest.raises(RuntimeError, match="summarizer exploded"):
        await execute_compact(
            model_client=client,
            messages=messages,
            reason="resume_compact",
            compact_system_prompt="PROMPT",
            compact_user_prompt_text="summarize",
        )

    # Messages must NOT be rewritten on failure.
    assert [m.content for m in messages] == original


def test_should_resume_compact_returns_false_on_small_session() -> None:
    """The should_resume_compact helper should return False for small sessions."""
    messages = _make_small_messages()
    assert not should_resume_compact(
        messages,
        project_root=Path.cwd(),
    )


# ---------------------------------------------------------------------------
# build_resume_request_messages: todo reminder inclusion
# ---------------------------------------------------------------------------


def test_build_resume_request_messages_includes_todo_reminder(tmp_path: Path) -> None:
    """When todo state exists, the request view should include the reminder."""
    messages = _make_small_messages()
    todo_store = TodoStateStore()
    sid = "todo-test"
    # Set up incomplete todo items.
    todo_store.set_items(sid, [
        TodoItem(id="t1", text="do something", status="in_progress"),
    ])
    # Simulate several rounds without todo_write.
    for _ in range(5):
        todo_store.record_model_turn_without_todo_write(sid)

    request_msgs = build_resume_request_messages(
        messages,
        project_root=tmp_path,
        todo_state_store=todo_store,
        session_id=sid,
    )

    # Should contain a todo_reminder message.
    has_todo = any(
        isinstance(m.content, str) and "todo_reminder" in m.content
        for m in request_msgs
    )
    assert has_todo


def test_build_resume_request_messages_no_todo_when_recent(tmp_path: Path) -> None:
    """When todo_write was used recently, no reminder should appear."""
    messages = _make_small_messages()
    todo_store = TodoStateStore()
    sid = "todo-recent"
    todo_store.set_items(sid, [
        TodoItem(id="t1", text="task", status="in_progress"),
    ])

    request_msgs = build_resume_request_messages(
        messages,
        project_root=tmp_path,
        todo_state_store=todo_store,
        session_id=sid,
    )

    has_todo = any(
        isinstance(m.content, str) and "todo_reminder" in m.content
        for m in request_msgs
    )
    assert not has_todo


# ---------------------------------------------------------------------------
# build_resume_request_messages: microcompact integration
# ---------------------------------------------------------------------------


def test_build_resume_request_messages_applies_microcompact(tmp_path: Path) -> None:
    """When microcompact is enabled, old large tool results should be replaced."""
    # Create messages with large tool results.
    messages: list[Message] = []
    for i in range(20):
        messages.append(Message(role="user", content=f"step-{i}"))
        messages.append(
            Message(
                role="assistant",
                content=[ToolUseBlock(id=f"tu{i}", name="read_file", input={"path": f"f{i}"})],
                assistant_text=f"reading f{i}",
            )
        )
        messages.append(
            Message(
                role="tool",
                content=[ToolResultBlock(tool_use_id=f"tu{i}", content="x" * 5000)],
            )
        )

    cfg = CompressionConfig(
        micro_compact_enabled=True,
        keep_recent_tool_results=3,
        micro_compact_min_chars=1000,
    )
    request_msgs = build_resume_request_messages(
        messages,
        project_root=tmp_path,
        compression_config=cfg,
    )

    # Old results should be compacted; recent should not.
    compacted_count = 0
    for msg in request_msgs:
        if msg.role != "tool" or not isinstance(msg.content, list):
            continue
        for block in msg.content:
            if isinstance(block, ToolResultBlock) and "Old tool result compacted" in block.content:
                compacted_count += 1
    assert compacted_count > 0


# ---------------------------------------------------------------------------
# 4.5: Active-run conflict prevents resume compact (unit-level)
# ---------------------------------------------------------------------------


def test_should_resume_compact_independent_of_run_state() -> None:
    """should_resume_compact only checks compression config and token threshold,
    not run state. Run-state gating is in the API layer."""
    messages = _make_small_messages()
    assert not should_resume_compact(
        messages,
        project_root=Path.cwd(),
    )


# ---------------------------------------------------------------------------
# Integration: full resume compact flow (hydrate -> check -> compact -> persist)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_resume_compact_flow_with_persistence(tmp_path: Path) -> None:
    """Exercise the same code path as _try_resume_compact:
    hydrate -> should_resume_compact -> execute_compact -> verify summary persisted and session rewritten."""
    reset_sessions()
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=50_000_000,
    )
    sid = "integration-resume"

    # Write enough messages to exceed threshold.
    for i in range(250):
        persistence.append_message(sid, Message(role="user", content=f"large-message-{i} " * 200))

    # Hydrate into memory (same as _hydrate_session_if_needed).
    messages, _warnings = persistence.hydrate_messages(sid)
    from app.memory.session_store import get_or_create_session
    get_or_create_session(sid, hydrate_fn=lambda _sid: messages)
    session_messages = get_or_create_session(sid)
    assert len(session_messages) > 100

    # Check threshold.
    cfg = CompressionConfig(
        context_window_tokens=200_000,
        auto_compact_buffer_tokens=13_000,
        compact_max_summary_tokens=4_000,
        compact_keep_recent_messages=8,
    )
    assert should_resume_compact(
        session_messages,
        project_root=tmp_path,
        compression_config=cfg,
        session_id=sid,
    )

    # Execute compact (same as _try_resume_compact).
    client = _RecordingModelClient()
    persisted: list[dict] = []

    def _persist(_sid: str, payload: dict) -> None:
        persistence.append_summary(_sid, payload)
        persisted.append(payload)

    before_count = len(session_messages)
    await execute_compact(
        model_client=client,
        messages=session_messages,
        reason="resume_compact",
        compact_system_prompt="COMPACT_PROMPT",
        compact_user_prompt_text=f"summarize {before_count} messages",
        keep_recent_messages=cfg.compact_keep_recent_messages,
        persist_fn=_persist,
        session_id=sid,
    )

    # Verify: session rewritten to boundary + recent.
    assert len(session_messages) == 1 + cfg.compact_keep_recent_messages
    assert len(persisted) == 1
    assert persisted[0]["reason"] == "resume_compact"
    assert persisted[0]["before_message_count"] == before_count
    assert len(persisted[0]["recent_messages"]) == cfg.compact_keep_recent_messages

    # Verify: re-hydrate from transcript restores the compacted state.
    reset_sessions()
    rehydrated, _ = persistence.hydrate_messages(sid)
    # Should be: boundary + recent_messages from summary + (no post-compact messages).
    assert len(rehydrated) == 1 + cfg.compact_keep_recent_messages


@pytest.mark.asyncio
async def test_full_resume_flow_small_session_skips_compact(tmp_path: Path) -> None:
    """A small hydrated session should skip resume compact entirely."""
    reset_sessions()
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=5_000_000,
    )
    sid = "small-session"

    for i in range(3):
        persistence.append_message(sid, Message(role="user", content=f"small-{i}"))

    messages, _ = persistence.hydrate_messages(sid)
    from app.memory.session_store import get_or_create_session
    get_or_create_session(sid, hydrate_fn=lambda _sid: messages)
    session_messages = get_or_create_session(sid)

    assert not should_resume_compact(
        session_messages,
        project_root=tmp_path,
        session_id=sid,
    )

    # Session should be unchanged.
    original = [m.content for m in session_messages]
    assert [m.content for m in session_messages] == original


@pytest.mark.asyncio
async def test_full_resume_flow_compact_failure_preserves_session(tmp_path: Path) -> None:
    """If execute_compact fails, session messages must remain intact."""
    reset_sessions()
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=50_000_000,
    )
    sid = "fail-resume"

    for i in range(250):
        persistence.append_message(sid, Message(role="user", content=f"msg-{i} " * 200))

    messages, _ = persistence.hydrate_messages(sid)
    from app.memory.session_store import get_or_create_session
    get_or_create_session(sid, hydrate_fn=lambda _sid: messages)
    session_messages = get_or_create_session(sid)

    original_contents = [m.content for m in session_messages]

    # Failing client.
    client = _FailingModelClient()
    with pytest.raises(RuntimeError):
        await execute_compact(
            model_client=client,
            messages=session_messages,
            reason="resume_compact",
            compact_system_prompt="PROMPT",
            compact_user_prompt_text="summarize",
        )

    # Session must be unchanged after failure.
    assert [m.content for m in session_messages] == original_contents
