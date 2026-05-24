"""JSONL transcript append/read for session persistence (M0.5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.memory.session_id import validate_session_id

TranscriptEntryType = Literal["message", "agent_event", "session_meta", "summary", "todo_state"]
SCHEMA_VERSION = 1


class TranscriptEntry(BaseModel):
    entry_id: str
    session_id: str
    type: TranscriptEntryType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    project_root: str
    schema_version: int = SCHEMA_VERSION
    payload: dict[str, Any] = Field(default_factory=dict)


class TranscriptTooLargeError(Exception):
    """Raised when a transcript file exceeds the configured byte limit."""


def new_entry_id() -> str:
    return f"evt_{uuid4().hex[:12]}"


class TranscriptStore:
    def __init__(self, *, storage_dir: Path, transcript_max_bytes: int) -> None:
        self._storage_dir = storage_dir.resolve()
        self._sessions_dir = self._storage_dir / "sessions"
        self._transcripts_dir = self._sessions_dir / "transcripts"
        self._transcript_max_bytes = transcript_max_bytes

    def ensure_dirs(self) -> None:
        self._transcripts_dir.mkdir(parents=True, exist_ok=True)

    def transcript_path(self, session_id: str) -> Path:
        validate_session_id(session_id)
        return self._transcripts_dir / f"{session_id}.jsonl"

    def relative_transcript_path(self, session_id: str) -> str:
        validate_session_id(session_id)
        return str(Path(self._storage_dir.name) / "sessions" / "transcripts" / f"{session_id}.jsonl")

    def append_entry(self, session_id: str, entry: TranscriptEntry) -> None:
        validate_session_id(session_id)
        self.ensure_dirs()
        path = self.transcript_path(session_id)
        if path.exists() and path.stat().st_size >= self._transcript_max_bytes:
            raise TranscriptTooLargeError(
                f"transcript for {session_id} exceeds {self._transcript_max_bytes} bytes"
            )
        line = entry.model_dump_json() + "\n"
        encoded = line.encode("utf-8")
        if len(encoded) > self._transcript_max_bytes:
            raise TranscriptTooLargeError(
                f"transcript entry exceeds {self._transcript_max_bytes} bytes"
            )
        if path.exists() and path.stat().st_size + len(encoded) > self._transcript_max_bytes:
            raise TranscriptTooLargeError(
                f"transcript for {session_id} exceeds {self._transcript_max_bytes} bytes"
            )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def read_transcript(self, session_id: str) -> tuple[list[TranscriptEntry], list[str]]:
        validate_session_id(session_id)
        path = self.transcript_path(session_id)
        if not path.exists():
            return [], []
        entries: list[TranscriptEntry] = []
        warnings: list[str] = []
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                entries.append(TranscriptEntry.model_validate_json(line))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"line {line_number}: skipped corrupt entry ({exc})")
        return entries, warnings

    def delete_transcript(self, session_id: str) -> bool:
        validate_session_id(session_id)
        path = self.transcript_path(session_id)
        if not path.exists():
            return False
        path.unlink()
        return True
