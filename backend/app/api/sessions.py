"""HTTP command routes for the runtime API."""

from __future__ import annotations

import re
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.deps import (
    build_api_policy,
    build_runtime_tools,
    get_app_settings,
    get_run_manager,
    resolve_model_client,
)
from app.api.errors import api_error
from app.api.runtime_service import cancel_task, schedule_run
from app.api.schemas import (
    CommandAck,
    CreateSessionRequest,
    CreateSessionResponse,
    PermissionDecisionRequest,
    SendMessageRequest,
    SendMessageResponse,
)
from app.core.config import Settings
from app.model_client import ModelClientError
from app.runtime.run_manager import RunManager

router = APIRouter()

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def _validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise api_error(
            400,
            error_type="validation_error",
            message="session_id must be 1-80 chars of letters, digits, underscore, or hyphen",
        )


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(body: CreateSessionRequest | None = None) -> CreateSessionResponse:
    requested = body.session_id if body else None
    if requested is None:
        return CreateSessionResponse(session_id=f"sess_{uuid4().hex[:12]}")
    _validate_session_id(requested)
    return CreateSessionResponse(session_id=requested)


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    settings: Settings = Depends(get_app_settings),
    run_manager: RunManager = Depends(get_run_manager),
) -> SendMessageResponse:
    _validate_session_id(session_id)
    message = body.message.strip()
    if not message:
        raise api_error(400, error_type="validation_error", message="message must not be empty")

    try:
        model_client = resolve_model_client(settings)
    except ModelClientError as exc:
        raise api_error(500, error_type="internal_error", message=str(exc)) from exc

    run_id = await run_manager.start_run_if_idle(session_id=session_id)
    if run_id is None:
        raise api_error(
            409,
            error_type="conflict",
            message="session already has an active run",
        )
    tools = build_runtime_tools(settings)
    policy = build_api_policy(settings)

    schedule_run(
        run_manager=run_manager,
        run_id=run_id,
        session_id=session_id,
        message=message,
        model_client=model_client,
        tools=tools,
        policy=policy,
        max_steps=settings.max_steps,
        max_session_messages=settings.max_session_messages,
    )

    return SendMessageResponse(run_id=run_id, session_id=session_id, accepted=True)


@router.post("/runs/{run_id}/permission", response_model=CommandAck)
async def resolve_permission(
    run_id: str,
    body: PermissionDecisionRequest,
    run_manager: RunManager = Depends(get_run_manager),
) -> CommandAck:
    state = run_manager.get_run(run_id)
    if state is None:
        raise api_error(404, error_type="not_found", message=f"unknown run_id: {run_id}")
    if state.status == "cancelled":
        raise api_error(
            409,
            error_type="permission_not_pending",
            message="run is cancelled",
        )
    if state.status not in {"running", "waiting_permission"}:
        raise api_error(
            409,
            error_type="run_not_active",
            message=f"run is not active (status={state.status})",
        )

    event = await run_manager.resolve_permission(
        run_id=run_id,
        permission_request_id=body.permission_request_id,
        decision=body.decision,  # type: ignore[arg-type]
    )
    if event is not None and event.type == "error":
        message = str(event.payload.get("error", ""))
        if "already resolved" in message or "stale permission_request_id" in message:
            raise api_error(409, error_type="permission_not_pending", message=message)
        raise api_error(404, error_type="not_found", message=message)

    return CommandAck(run_id=run_id, accepted=True)


@router.post("/runs/{run_id}/cancel", response_model=CommandAck)
async def cancel_run(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> CommandAck:
    state = run_manager.get_run(run_id)
    if state is None:
        raise api_error(404, error_type="not_found", message=f"unknown run_id: {run_id}")

    if state.status == "cancelled":
        return CommandAck(run_id=run_id, accepted=True)

    if state.status not in {"running", "waiting_permission"}:
        raise api_error(
            409,
            error_type="conflict",
            message=f"run already terminal (status={state.status})",
        )

    cancel_task(run_id)
    await run_manager.cancel_run(run_id)
    return CommandAck(run_id=run_id, accepted=True)
