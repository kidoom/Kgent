"""HTTP command routes for the runtime API."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.deps import (
    build_api_policy,
    build_runtime_tools,
    get_app_settings,
    get_persistence_service,
    get_run_manager,
    get_todo_state_store,
    resolve_model_client,
)
from app.api.errors import api_error
from app.api.runtime_service import cancel_task, schedule_run
from app.api.schemas import (
    CommandAck,
    CreateSessionRequest,
    CreateSessionResponse,
    DeleteSessionResponse,
    PermissionDecisionRequest,
    SendMessageRequest,
    SendMessageResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
    TranscriptEntryResponse,
    TranscriptResponse,
)
from app.core.config import Settings
from app.memory.persistence import PersistenceError, PersistenceService
from app.memory.session_id import validate_session_id
from app.memory.session_store import delete_session as delete_memory_session
from app.memory.session_store import get_or_create_session, has_session
from app.model_client import ModelClientError
from app.runtime.run_manager import RunManager
from app.runtime.todo_state import TodoStateStore

router = APIRouter()


def _validate_session_id_or_400(session_id: str) -> None:
    try:
        validate_session_id(session_id)
    except ValueError as exc:
        raise api_error(400, error_type="validation_error", message=str(exc)) from exc


def _session_summary(meta) -> SessionSummary:
    return SessionSummary(
        session_id=meta.session_id,
        title=meta.title,
        first_prompt=meta.first_prompt,
        last_prompt=meta.last_prompt,
        project_root=meta.project_root,
        created_at=meta.created_at,
        updated_at=meta.updated_at,
        message_count=meta.message_count,
        event_count=meta.event_count,
    )


def _hydrate_session_if_needed(
    session_id: str,
    persistence: PersistenceService,
) -> None:
    if has_session(session_id):
        return

    def hydrate_fn(sid: str):
        messages, _warnings = persistence.hydrate_messages(sid)
        return messages

    get_or_create_session(session_id, hydrate_fn=hydrate_fn)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    persistence: PersistenceService = Depends(get_persistence_service),
) -> SessionListResponse:
    sessions = [_session_summary(meta) for meta in persistence.list_sessions()]
    return SessionListResponse(sessions=sessions)


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest | None = None,
    settings: Settings = Depends(get_app_settings),
    persistence: PersistenceService = Depends(get_persistence_service),
) -> CreateSessionResponse:
    requested = body.session_id if body else None
    session_id = requested or f"sess_{uuid4().hex[:12]}"
    _validate_session_id_or_400(session_id)
    persistence.ensure_session(session_id)
    persistence.append_session_meta(
        session_id,
        {
            "title": "New session",
            "project_root": str(settings.project_root),
            "permission_mode": settings.permission_mode,
        },
    )
    return CreateSessionResponse(session_id=session_id)


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    persistence: PersistenceService = Depends(get_persistence_service),
) -> SessionDetailResponse:
    _validate_session_id_or_400(session_id)
    meta = persistence.get_session(session_id)
    if meta is None:
        raise api_error(404, error_type="not_found", message=f"unknown session_id: {session_id}")
    return SessionDetailResponse(
        **_session_summary(meta).model_dump(),
        transcript_path=meta.transcript_path,
    )


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session_record(
    session_id: str,
    persistence: PersistenceService = Depends(get_persistence_service),
    run_manager: RunManager = Depends(get_run_manager),
    todo_state_store: TodoStateStore = Depends(get_todo_state_store),
) -> DeleteSessionResponse:
    _validate_session_id_or_400(session_id)
    if run_manager.has_active_run(session_id):
        raise api_error(
            409,
            error_type="conflict",
            message="cannot delete a session with an active run",
        )
    deleted = persistence.delete_session(session_id)
    if not deleted:
        raise api_error(404, error_type="not_found", message=f"unknown session_id: {session_id}")
    delete_memory_session(session_id)
    run_manager.clear_session_history(session_id)
    todo_state_store.forget(session_id)
    return DeleteSessionResponse(session_id=session_id, deleted=True)


@router.get("/sessions/{session_id}/transcript", response_model=TranscriptResponse)
async def get_session_transcript(
    session_id: str,
    persistence: PersistenceService = Depends(get_persistence_service),
) -> TranscriptResponse:
    _validate_session_id_or_400(session_id)
    if persistence.get_session(session_id) is None:
        raise api_error(404, error_type="not_found", message=f"unknown session_id: {session_id}")
    entries, warnings = persistence.load_transcript(session_id)
    return TranscriptResponse(
        session_id=session_id,
        entries=[
            TranscriptEntryResponse(
                entry_id=entry.entry_id,
                session_id=entry.session_id,
                type=entry.type,
                created_at=entry.created_at,
                project_root=entry.project_root,
                schema_version=entry.schema_version,
                payload=entry.payload,
            )
            for entry in entries
        ],
        warnings=warnings,
    )


@router.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    settings: Settings = Depends(get_app_settings),
    run_manager: RunManager = Depends(get_run_manager),
    persistence: PersistenceService = Depends(get_persistence_service),
    todo_state_store: TodoStateStore = Depends(get_todo_state_store),
) -> SendMessageResponse:
    _validate_session_id_or_400(session_id)
    message = body.message.strip()
    if not message:
        raise api_error(400, error_type="validation_error", message="message must not be empty")

    try:
        model_client = resolve_model_client(settings)
    except ModelClientError as exc:
        raise api_error(500, error_type="internal_error", message=str(exc)) from exc

    try:
        persistence.ensure_session(session_id)
        _hydrate_session_if_needed(session_id, persistence)
        todo_state_store.hydrate(session_id, persistence.load_todo_state_payload(session_id))
    except PersistenceError as exc:
        raise api_error(409, error_type="transcript_too_large", message=str(exc)) from exc

    run_id = await run_manager.start_run_if_idle(session_id=session_id)
    if run_id is None:
        raise api_error(
            409,
            error_type="conflict",
            message="session already has an active run",
        )
    tools = build_runtime_tools(
        settings,
        session_id=session_id,
        persistence=persistence,
        todo_state_store=todo_state_store,
    )
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
        project_root=settings.project_root,
        persistence=persistence,
        todo_state_store=todo_state_store,
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
