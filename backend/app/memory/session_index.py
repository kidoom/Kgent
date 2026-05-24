"""session_index.json read/write for sidebar session list (M0.5)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.memory.session_id import validate_session_id

INDEX_SCHEMA_VERSION = 1


class SessionMeta(BaseModel):
    session_id: str
    title: str = ""
    first_prompt: str = ""
    last_prompt: str = ""
    project_root: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0
    event_count: int = 0
    transcript_path: str = ""


class SessionIndex(BaseModel):
    schema_version: int = INDEX_SCHEMA_VERSION
    sessions: list[SessionMeta] = Field(default_factory=list)


class SessionIndexStore:
    def __init__(self, *, storage_dir: Path) -> None:
        self._sessions_dir = (storage_dir / "sessions").resolve()
        self._index_path = self._sessions_dir / "session_index.json"

    def ensure_dirs(self) -> None:
        self._sessions_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> SessionIndex:
        self.ensure_dirs()
        if not self._index_path.exists():
            return SessionIndex()
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            return SessionIndex.model_validate(data)
        except Exception:
            return SessionIndex()

    def save(self, index: SessionIndex) -> None:
        self.ensure_dirs()
        tmp_path = self._index_path.with_suffix(".json.tmp")
        payload = index.model_dump(mode="json")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self._index_path)

    def list_sessions(self) -> list[SessionMeta]:
        sessions = self.load().sessions
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def get_session(self, session_id: str) -> SessionMeta | None:
        validate_session_id(session_id)
        for session in self.load().sessions:
            if session.session_id == session_id:
                return session
        return None

    def upsert_session(self, meta: SessionMeta) -> None:
        validate_session_id(meta.session_id)
        index = self.load()
        updated = False
        for position, existing in enumerate(index.sessions):
            if existing.session_id == meta.session_id:
                index.sessions[position] = meta
                updated = True
                break
        if not updated:
            index.sessions.append(meta)
        self.save(index)

    def delete_session(self, session_id: str) -> bool:
        validate_session_id(session_id)
        index = self.load()
        remaining = [session for session in index.sessions if session.session_id != session_id]
        if len(remaining) == len(index.sessions):
            return False
        index.sessions = remaining
        self.save(index)
        return True
