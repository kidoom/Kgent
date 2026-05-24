"""Tests for M0.5 transcript persistence."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import fake_model  # noqa: F401

from app.core.config import Settings, reload_settings
from app.memory.persistence import PersistenceError, build_persistence_service
from app.memory.session_store import get_or_create_session, reset_sessions
from app.memory.transcript_store import (
    TranscriptEntry,
    TranscriptStore,
    TranscriptTooLargeError,
    new_entry_id,
)
from app.runtime.messages import Message, ToolResultBlock, ToolUseBlock


@pytest.fixture
def storage(tmp_path: Path):
    reset_sessions()
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=1024,
        disabled=False,
    )
    yield persistence
    reset_sessions()


def test_append_message_round_trip(storage, tmp_path: Path) -> None:
    storage.ensure_session("sess_test1")
    storage.append_message("sess_test1", Message(role="user", content="hello"))
    entries, warnings = storage.load_transcript("sess_test1")
    assert not warnings
    assert len(entries) == 1
    assert entries[0].type == "message"
    assert entries[0].payload["content"] == "hello"


def test_append_message_creates_missing_session_without_deadlock(tmp_path: Path) -> None:
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent",
        project_root=tmp_path,
        transcript_max_bytes=1024,
        disabled=False,
    )
    error: list[BaseException] = []

    def append() -> None:
        try:
            persistence.append_message("sess_auto", Message(role="user", content="hello"))
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    thread = threading.Thread(target=append, daemon=True)
    thread.start()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert not error
    assert persistence.get_session("sess_auto") is not None


def test_append_tool_result_round_trip(storage) -> None:
    storage.ensure_session("sess_tool")
    tool_use = ToolUseBlock(id="toolu_1", name="read_file", input={"path": "README.md"})
    storage.append_message(
        "sess_tool",
        Message(role="assistant", content=[tool_use], assistant_text="reading"),
    )
    storage.append_message(
        "sess_tool",
        Message(
            role="user",
            content=[ToolResultBlock(tool_use_id="toolu_1", content="file body", is_error=False)],
        ),
    )
    messages, _ = storage.hydrate_messages("sess_tool")
    assert len(messages) == 2
    assert isinstance(messages[1].content, list)
    assert messages[1].content[0].content == "file body"


def test_no_meta_context_persistence(storage) -> None:
    storage.ensure_session("sess_meta")
    storage.append_message(
        "sess_meta",
        Message(role="user", content="<system-reminder>secret</system-reminder>", is_meta=True),
    )
    entries, _ = storage.load_transcript("sess_meta")
    assert entries == []


def test_corrupt_line_tolerance(storage, tmp_path: Path) -> None:
    storage.ensure_session("sess_bad")
    path = storage._transcript.transcript_path("sess_bad")  # noqa: SLF001
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"bad": true}\n', encoding="utf-8")
    storage.append_message("sess_bad", Message(role="user", content="ok"))
    entries, warnings = storage.load_transcript("sess_bad")
    assert len(entries) == 1
    assert warnings


def test_index_atomic_write(storage) -> None:
    storage.ensure_session("sess_idx")
    storage.append_message("sess_idx", Message(role="user", content="one"), user_prompt="one")
    index_path = storage._index._index_path  # noqa: SLF001
    json.loads(index_path.read_text(encoding="utf-8"))
    meta = storage.get_session("sess_idx")
    assert meta is not None
    assert meta.message_count == 1
    assert meta.title == "one"


def test_custom_storage_dir_transcript_path(tmp_path: Path) -> None:
    persistence = build_persistence_service(
        storage_dir=tmp_path / ".kgent-dev",
        project_root=tmp_path,
        transcript_max_bytes=1024,
        disabled=False,
    )
    meta = persistence.ensure_session("sess_custom")

    assert meta.transcript_path == str(Path(".kgent-dev") / "sessions" / "transcripts" / "sess_custom.jsonl")


def test_session_id_validation_blocks_traversal(storage) -> None:
    with pytest.raises(ValueError):
        storage.load_transcript("../evil")


def test_transcript_max_bytes(storage) -> None:
    storage.ensure_session("sess_big")
    storage.append_message("sess_big", Message(role="user", content="small"))
    big = "x" * 900
    with pytest.raises(PersistenceError):
        storage.append_message("sess_big", Message(role="user", content=big))


def test_hydrate_after_restart(storage) -> None:
    storage.ensure_session("sess_hydrate")
    storage.append_message("sess_hydrate", Message(role="user", content="hello"), user_prompt="hello")
    storage.append_message("sess_hydrate", Message(role="assistant", content="hi there"))
    reset_sessions()
    messages, _ = storage.hydrate_messages("sess_hydrate")
    assert len(messages) == 2
    get_or_create_session("sess_hydrate", hydrate_fn=lambda _sid: messages)
    assert get_or_create_session("sess_hydrate")[0].content == "hello"


def test_list_sessions_sorted_by_updated_at(storage) -> None:
    storage.ensure_session("sess_a")
    storage.append_message("sess_a", Message(role="user", content="a"), user_prompt="a")
    storage.ensure_session("sess_b")
    storage.append_message("sess_b", Message(role="user", content="b"), user_prompt="b")
    sessions = storage.list_sessions()
    assert sessions[0].session_id == "sess_b"


def test_delete_session_removes_index_and_transcript(storage) -> None:
    storage.ensure_session("sess_delete")
    storage.append_message("sess_delete", Message(role="user", content="bye"), user_prompt="bye")
    path = storage._transcript.transcript_path("sess_delete")  # noqa: SLF001
    assert path.exists()

    assert storage.delete_session("sess_delete") is True
    assert storage.get_session("sess_delete") is None
    assert not path.exists()
    assert storage.delete_session("sess_delete") is False


def test_todo_state_round_trip(storage) -> None:
    storage.ensure_session("sess_todo_state")
    payload = {
        "items": [{"id": "a", "text": "plan", "status": "in_progress"}],
        "updated_at": "2026-05-24T00:00:00Z",
        "rounds_since_todo_write": 0,
    }

    storage.append_todo_state("sess_todo_state", payload)

    entries, _warnings = storage.load_transcript("sess_todo_state")
    assert entries[-1].type == "todo_state"
    assert storage.load_todo_state_payload("sess_todo_state") == payload


def test_transcript_store_rejects_oversized_before_append(tmp_path: Path) -> None:
    store = TranscriptStore(storage_dir=tmp_path / ".kgent", transcript_max_bytes=20)
    entry = TranscriptEntry(
        entry_id=new_entry_id(),
        session_id="sess_x",
        type="message",
        project_root=str(tmp_path),
        payload={"role": "user", "content": "hello"},
    )
    with pytest.raises(TranscriptTooLargeError):
        store.append_entry("sess_x", entry)
