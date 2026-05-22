"""Request / response models for the HTTP runtime API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    session_id: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str


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
