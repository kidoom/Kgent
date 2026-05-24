"""Unified persistence facade for transcript + session index (M0.5)."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.memory.session_id import validate_session_id
from app.memory.session_index import SessionIndexStore, SessionMeta
from app.memory.transcript_store import (
    TranscriptEntry,
    TranscriptStore,
    TranscriptTooLargeError,
    new_entry_id,
)
from app.runtime.messages import Message, ToolResultBlock, ToolUseBlock
from app.runtime.protocol import AgentEvent

TITLE_MAX_LEN = 60
_lock = threading.RLock()


class PersistenceError(Exception):
    """Raised when transcript/index persistence fails."""


class PersistenceService:
    def __init__(
        self,
        *,
        storage_dir: Path,
        project_root: Path,
        transcript_max_bytes: int,
        disabled: bool = False,
    ) -> None:
        self._project_root = project_root.resolve()
        self._disabled = disabled
        self._transcript = TranscriptStore(
            storage_dir=storage_dir,
            transcript_max_bytes=transcript_max_bytes,
        )
        self._index = SessionIndexStore(storage_dir=storage_dir)

    @property
    def disabled(self) -> bool:
        return self._disabled

    def ensure_session(self, session_id: str) -> SessionMeta:
        validate_session_id(session_id)
        if self._disabled:
            return self._placeholder_meta(session_id)
        with _lock:
            existing = self._index.get_session(session_id)
            if existing is not None:
                return existing
            now = datetime.now(timezone.utc)
            meta = SessionMeta(
                session_id=session_id,
                title="New session",
                project_root=str(self._project_root),
                created_at=now,
                updated_at=now,
                transcript_path=self._transcript.relative_transcript_path(session_id),
            )
            self._index.upsert_session(meta)
            return meta

    def append_message(
        self,
        session_id: str,
        message: Message,
        *,
        user_prompt: str | None = None,
    ) -> None:
        if self._disabled or message.is_meta:
            return
        validate_session_id(session_id)
        entry = TranscriptEntry(
            entry_id=new_entry_id(),
            session_id=session_id,
            type="message",
            project_root=str(self._project_root),
            payload=message.model_dump(mode="json"),
        )
        with _lock:
            try:
                self._transcript.append_entry(session_id, entry)
            except TranscriptTooLargeError as exc:
                raise PersistenceError(str(exc)) from exc
            meta = self._index.get_session(session_id) or self.ensure_session(session_id)
            meta.message_count += 1
            meta.updated_at = datetime.now(timezone.utc)
            if user_prompt:
                prompt = user_prompt.strip()
                if prompt:
                    if not meta.first_prompt:
                        meta.first_prompt = prompt
                        meta.title = _truncate_title(prompt)
                    meta.last_prompt = prompt
            self._index.upsert_session(meta)

    def append_agent_event(self, session_id: str, event: AgentEvent) -> None:
        if self._disabled:
            return
        validate_session_id(session_id)
        entry = TranscriptEntry(
            entry_id=new_entry_id(),
            session_id=session_id,
            type="agent_event",
            project_root=str(self._project_root),
            payload=event.model_dump(mode="json"),
        )
        with _lock:
            try:
                self._transcript.append_entry(session_id, entry)
            except TranscriptTooLargeError as exc:
                raise PersistenceError(str(exc)) from exc
            meta = self._index.get_session(session_id) or self.ensure_session(session_id)
            meta.event_count += 1
            meta.updated_at = datetime.now(timezone.utc)
            self._index.upsert_session(meta)

    def append_session_meta(self, session_id: str, payload: dict[str, Any]) -> None:
        if self._disabled:
            return
        validate_session_id(session_id)
        entry = TranscriptEntry(
            entry_id=new_entry_id(),
            session_id=session_id,
            type="session_meta",
            project_root=str(self._project_root),
            payload=payload,
        )
        with _lock:
            try:
                self._transcript.append_entry(session_id, entry)
            except TranscriptTooLargeError as exc:
                raise PersistenceError(str(exc)) from exc
            meta = self._index.get_session(session_id) or self.ensure_session(session_id)
            title = payload.get("title")
            if isinstance(title, str) and title.strip():
                meta.title = _truncate_title(title.strip())
            meta.updated_at = datetime.now(timezone.utc)
            self._index.upsert_session(meta)

    def append_todo_state(self, session_id: str, payload: dict[str, Any]) -> None:
        if self._disabled:
            return
        validate_session_id(session_id)
        entry = TranscriptEntry(
            entry_id=new_entry_id(),
            session_id=session_id,
            type="todo_state",
            project_root=str(self._project_root),
            payload=payload,
        )
        with _lock:
            try:
                self._transcript.append_entry(session_id, entry)
            except TranscriptTooLargeError as exc:
                raise PersistenceError(str(exc)) from exc
            meta = self._index.get_session(session_id) or self.ensure_session(session_id)
            meta.updated_at = datetime.now(timezone.utc)
            self._index.upsert_session(meta)

    def list_sessions(self) -> list[SessionMeta]:
        if self._disabled:
            return []
        return self._index.list_sessions()

    def get_session(self, session_id: str) -> SessionMeta | None:
        if self._disabled:
            return None
        return self._index.get_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        validate_session_id(session_id)
        if self._disabled:
            return False
        with _lock:
            deleted_index = self._index.delete_session(session_id)
            deleted_transcript = self._transcript.delete_transcript(session_id)
        return deleted_index or deleted_transcript

    def load_transcript(self, session_id: str) -> tuple[list[TranscriptEntry], list[str]]:
        validate_session_id(session_id)
        if self._disabled:
            return [], []
        return self._transcript.read_transcript(session_id)

    def load_todo_state_payload(self, session_id: str) -> dict[str, Any] | None:
        entries, _warnings = self.load_transcript(session_id)
        for entry in reversed(entries):
            if entry.type == "todo_state":
                return entry.payload
        return None

    def hydrate_messages(self, session_id: str) -> tuple[list[Message], list[str]]:
        entries, warnings = self.load_transcript(session_id)
        raw_messages: list[Message] = []
        for entry in entries:
            if entry.type != "message":
                continue
            try:
                message = Message.model_validate(entry.payload)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"entry {entry.entry_id}: skipped invalid message ({exc})")
                continue
            if message.is_meta:
                continue
            raw_messages.append(message)
        repaired, repair_warnings = _repair_messages(raw_messages)
        warnings.extend(repair_warnings)
        return repaired, warnings

    def _placeholder_meta(self, session_id: str) -> SessionMeta:
        now = datetime.now(timezone.utc)
        return SessionMeta(
            session_id=session_id,
            title="New session",
            project_root=str(self._project_root),
            created_at=now,
            updated_at=now,
            transcript_path=self._transcript.relative_transcript_path(session_id),
        )


def build_persistence_service(
    *,
    storage_dir: Path,
    project_root: Path,
    transcript_max_bytes: int,
    disabled: bool = False,
) -> PersistenceService:
    return PersistenceService(
        storage_dir=storage_dir,
        project_root=project_root,
        transcript_max_bytes=transcript_max_bytes,
        disabled=disabled,
    )


def _truncate_title(text: str) -> str:
    text = text.strip()
    if len(text) <= TITLE_MAX_LEN:
        return text
    return text[: TITLE_MAX_LEN - 3].rstrip() + "..."


def _repair_messages(messages: list[Message]) -> tuple[list[Message], list[str]]:
    warnings: list[str] = []
    tool_use_ids: set[str] = set()
    tool_result_ids: set[str] = set()
    for message in messages:
        if message.role == "assistant" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    tool_use_ids.add(block.id)
        if message.role == "user" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    tool_result_ids.add(block.tool_use_id)

    valid_tool_use = tool_use_ids & tool_result_ids
    unpaired_uses = tool_use_ids - tool_result_ids
    orphan_results = tool_result_ids - tool_use_ids
    if unpaired_uses:
        warnings.append(f"dropped unpaired tool_use ids: {sorted(unpaired_uses)}")
    if orphan_results:
        warnings.append(f"skipped orphan tool_result ids: {sorted(orphan_results)}")

    repaired: list[Message] = []
    for message in messages:
        if message.role == "assistant" and isinstance(message.content, list):
            tool_uses = [block for block in message.content if isinstance(block, ToolUseBlock)]
            if tool_uses and not all(block.id in valid_tool_use for block in tool_uses):
                if message.assistant_text:
                    repaired.append(
                        Message(
                            role="assistant",
                            content=message.assistant_text,
                            assistant_text=message.assistant_text,
                        )
                    )
                continue
            repaired.append(message)
            continue

        if message.role == "user" and isinstance(message.content, list):
            blocks = [
                block
                for block in message.content
                if not (
                    isinstance(block, ToolResultBlock)
                    and block.tool_use_id not in valid_tool_use
                )
            ]
            if blocks:
                repaired.append(Message(role="user", content=blocks))
            continue

        repaired.append(message)

    return repaired, warnings
