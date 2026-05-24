"""Request / response models for the HTTP runtime API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    session_id: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str


class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted: bool = True


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    client_message_id: str | None = None


class SendMessageResponse(BaseModel):
    run_id: str
    session_id: str
    accepted: bool = True


class PermissionDecisionRequest(BaseModel):
    permission_request_id: str
    decision: Literal["allow", "deny"]


class CommandAck(BaseModel):
    run_id: str
    accepted: bool = True


class SessionSummary(BaseModel):
    session_id: str
    title: str = ""
    first_prompt: str = ""
    last_prompt: str = ""
    project_root: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    event_count: int = 0


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class SessionDetailResponse(SessionSummary):
    transcript_path: str = ""


class TranscriptEntryResponse(BaseModel):
    entry_id: str
    session_id: str
    type: str
    created_at: datetime
    project_root: str
    schema_version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)


class TranscriptResponse(BaseModel):
    session_id: str
    entries: list[TranscriptEntryResponse]
    warnings: list[str] = Field(default_factory=list)
