"""WebSocket runtime API for interactive agent runs (V0.2.1)."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.runtime.loop import RunCancelledError, run_agent_stream
from app.model_client import ModelClientError, ModelClientProtocol, build_model_client
from app.runtime.permissions import AllowAllPolicy, AskPolicy, RiskBasedPolicy
from app.runtime.protocol import (
    AgentEvent,
    CancelRunCommand,
    PermissionDecisionCommand,
    StartRunCommand,
    error_event,
)
from app.runtime.run_manager import RunManager, RunManagerHost
from app.core.config import get_settings
from app.tools.registry import build_tools

router = APIRouter(prefix="/api", tags=["runtime"])


def _resolve_ws_model_client(request: Request, provider: str, model_kwargs: dict[str, object]) -> tuple[ModelClientProtocol, bool]:
    shared = getattr(request.app.state, "model_client", None)
    if shared is not None and provider == "openai":
        return shared, False
    return build_model_client(provider, **model_kwargs), True


def _build_ws_policy(permission_mode: str):
    if permission_mode == "allow_all":
        return AllowAllPolicy()
    if permission_mode in {"interactive", "ask"}:
        return AskPolicy()
    return RiskBasedPolicy()


def _parse_command(raw: dict[str, Any]):
    cmd_type = raw.get("type")
    if cmd_type == "start_run":
        return StartRunCommand.model_validate(raw)
    if cmd_type == "permission_decision":
        return PermissionDecisionCommand.model_validate(raw)
    if cmd_type == "cancel_run":
        return CancelRunCommand.model_validate(raw)
    raise ValueError(f"unknown command type: {cmd_type}")


async def _send_event(websocket: WebSocket, event: AgentEvent) -> None:
    await websocket.send_json(event.model_dump(mode="json"))


async def _execute_run(
    *,
    run_manager: RunManager,
    run_id: str,
    session_id: str,
    message: str,
    model_client: ModelClientProtocol,
    tools: list,
    policy,
    max_steps: int,
    max_session_messages: int,
    websocket: WebSocket,
    owns_client: bool,
) -> None:
    host = RunManagerHost(run_manager, run_id, session_id)

    async def subscriber(event: AgentEvent) -> None:
        await _send_event(websocket, event)

    run_manager.subscribe(run_id, subscriber)

    try:
        await run_agent_stream(
            run_id=run_id,
            session_id=session_id,
            message=message,
            model_client=model_client,
            tools=tools,
            host=host,
            policy=policy,
            max_steps=max_steps,
            max_session_messages=max_session_messages,
        )
    except RunCancelledError:
        pass
    except ModelClientError as exc:
        state = run_manager.get_run(run_id)
        seq = (state.seq + 1) if state else 1
        await run_manager.record_event(
            error_event(
                run_id=run_id,
                session_id=session_id,
                seq=seq,
                error=str(exc),
            )
        )
        if state:
            state.status = "failed"
    except RuntimeError as exc:
        state = run_manager.get_run(run_id)
        seq = (state.seq + 1) if state else 1
        await run_manager.record_event(
            AgentEvent(
                type="run_failed",
                run_id=run_id,
                session_id=session_id,
                seq=seq,
                payload={"error": str(exc)},
            )
        )
    finally:
        if owns_client and hasattr(model_client, "close"):
            await model_client.close()


def _get_run_manager(app) -> RunManager:
    manager = getattr(app.state, "run_manager", None)
    if manager is None:
        manager = RunManager()
        app.state.run_manager = manager
    return manager


@router.websocket("/runtime")
async def runtime_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    settings = get_settings()
    run_manager = _get_run_manager(websocket.app)
    connection_id = uuid4().hex
    active_tasks: dict[str, asyncio.Task[None]] = {}

    try:
        while True:
            raw: dict[str, Any] = {}
            raw_text = await websocket.receive_text()
            try:
                parsed = json.loads(raw_text)
                if not isinstance(parsed, dict):
                    raise ValueError("command must be a JSON object")
                raw = parsed
                command = _parse_command(raw)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                await _send_event(
                    websocket,
                    error_event(
                        run_id=str(raw.get("run_id", "")),
                        session_id=str(raw.get("session_id", "")),
                        seq=1,
                        error=str(exc),
                    ),
                )
                continue

            if isinstance(command, StartRunCommand):
                try:
                    model_client, owns_client = _resolve_ws_model_client(
                        websocket,
                        settings.provider,
                        settings.model_kwargs,
                    )
                except ModelClientError as exc:
                    await _send_event(
                        websocket,
                        error_event(
                            run_id="",
                            session_id=command.session_id,
                            seq=1,
                            error=str(exc),
                        ),
                    )
                    continue

                run_id = run_manager.create_run(
                    session_id=command.session_id,
                    connection_id=connection_id,
                )
                tools = build_tools(settings.project_root)
                policy = _build_ws_policy(settings.permission_mode)

                task = asyncio.create_task(
                    _execute_run(
                        run_manager=run_manager,
                        run_id=run_id,
                        session_id=command.session_id,
                        message=command.message,
                        model_client=model_client,
                        tools=tools,
                        policy=policy,
                        max_steps=settings.max_steps,
                        max_session_messages=settings.max_session_messages,
                        websocket=websocket,
                        owns_client=owns_client,
                    )
                )
                active_tasks[run_id] = task

            elif isinstance(command, PermissionDecisionCommand):
                event = await run_manager.resolve_permission(
                    run_id=command.run_id,
                    permission_request_id=command.permission_request_id,
                    decision=command.decision,
                )
                if event is not None and event.type == "error":
                    await _send_event(websocket, event)

            elif isinstance(command, CancelRunCommand):
                event = await run_manager.cancel_run(command.run_id)
                if event is not None and event.type == "error":
                    await _send_event(websocket, event)
                task = active_tasks.pop(command.run_id, None)
                if task is not None and not task.done():
                    task.cancel()

    except WebSocketDisconnect:
        await run_manager.cancel_runs_for_connection(connection_id)
        for task in active_tasks.values():
            if not task.done():
                task.cancel()
