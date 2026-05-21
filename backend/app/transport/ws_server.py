"""Standalone WebSocket runtime server (V0.2.1 transport)."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from uuid import uuid4

import websockets
from pydantic import ValidationError
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Response
from websockets.server import ServerConnection
from websockets.typing import Origin, Subprotocol

from app.core.config import get_settings
from app.model_client import ModelClientError, ModelClientProtocol, available_providers, build_model_client
from app.runtime.loop import RunCancelledError, run_agent_stream
from app.runtime.permissions import AllowAllPolicy, AskPolicy, RiskBasedPolicy
from app.runtime.protocol import (
    AgentEvent,
    CancelRunCommand,
    PermissionDecisionCommand,
    StartRunCommand,
    error_event,
)
from app.runtime.run_manager import RunManager, RunManagerHost
from app.tools.registry import build_tools

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
RUNTIME_PATH = "/runtime"
HEALTH_PATH = "/health"

_run_manager = RunManager()
_shared_model_client: ModelClientProtocol | None = None


def get_run_manager() -> RunManager:
    return _run_manager


def _allowed_origins() -> set[str] | None:
    """Return allowed Origin header values, or None to allow all (local dev default)."""
    raw = os.environ.get("KGENT_WS_ORIGINS")
    if raw is None:
        return None
    stripped = raw.strip()
    if stripped in {"", "*"}:
        return None
    return {origin.strip() for origin in stripped.split(",") if origin.strip()}


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


async def _send_event(websocket: ServerConnection, event: AgentEvent) -> None:
    try:
        await websocket.send(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
    except ConnectionClosed:
        return


def _resolve_model_client(settings) -> tuple[ModelClientProtocol, bool]:
    global _shared_model_client
    if _shared_model_client is None:
        _shared_model_client = build_model_client(settings.provider, **settings.model_kwargs)
    return _shared_model_client, False


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
    websocket: ServerConnection,
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
        run_manager.unsubscribe(run_id)


async def _cancel_active_tasks(
    active_tasks: dict[str, asyncio.Task[None]],
    run_manager: RunManager,
) -> None:
    for run_id, task in list(active_tasks.items()):
        if task.done():
            active_tasks.pop(run_id, None)
            continue
        await run_manager.cancel_run(run_id)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, RunCancelledError):
            pass
        active_tasks.pop(run_id, None)


async def _handle_runtime_connection(websocket: ServerConnection) -> None:
    settings = get_settings()
    connection_id = uuid4().hex
    active_tasks: dict[str, asyncio.Task[None]] = {}

    try:
        while True:
            raw: dict[str, Any] = {}
            raw_text = await websocket.recv()
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
                    model_client, _owns_client = _resolve_model_client(settings)
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

                await _cancel_active_tasks(active_tasks, _run_manager)

                run_id = _run_manager.create_run(
                    session_id=command.session_id,
                    connection_id=connection_id,
                )
                tools = build_tools(settings.project_root)
                policy = _build_ws_policy(settings.permission_mode)

                task = asyncio.create_task(
                    _execute_run(
                        run_manager=_run_manager,
                        run_id=run_id,
                        session_id=command.session_id,
                        message=command.message,
                        model_client=model_client,
                        tools=tools,
                        policy=policy,
                        max_steps=settings.max_steps,
                        max_session_messages=settings.max_session_messages,
                        websocket=websocket,
                    )
                )
                active_tasks[run_id] = task
                task.add_done_callback(lambda _t, rid=run_id: active_tasks.pop(rid, None))

            elif isinstance(command, PermissionDecisionCommand):
                event = await _run_manager.resolve_permission(
                    run_id=command.run_id,
                    permission_request_id=command.permission_request_id,
                    decision=command.decision,
                )
                if event is not None and event.type == "error":
                    await _send_event(websocket, event)

            elif isinstance(command, CancelRunCommand):
                event = await _run_manager.cancel_run(command.run_id)
                if event is not None and event.type == "error":
                    await _send_event(websocket, event)
                task = active_tasks.pop(command.run_id, None)
                if task is not None and not task.done():
                    task.cancel()

    except ConnectionClosed:
        await _run_manager.cancel_runs_for_connection(connection_id)
        for task in active_tasks.values():
            if not task.done():
                task.cancel()


def _health_body() -> str:
    settings = get_settings()
    tool_risks = {
        tool.name: getattr(tool, "risk_level", "high")
        for tool in build_tools(settings.project_root)
    }
    payload = {
        "status": "ok",
        "provider": settings.provider,
        "available_providers": available_providers(),
        "model_client_ready": _shared_model_client is not None,
        "permission_mode": settings.permission_mode,
        "tool_risks": tool_risks,
    }
    return json.dumps(payload, ensure_ascii=False)


def _process_request(
    connection: ServerConnection,
    request: websockets.http11.Request,
) -> Response | None:
    if request.path == HEALTH_PATH:
        response = connection.respond(200, _health_body())
        response.headers["Content-Type"] = "application/json"
        return response
    if request.path != RUNTIME_PATH:
        return connection.respond(404, "Not Found")
    return None


def _select_subprotocol(
    connection: ServerConnection,
    subprotocols: list[Subprotocol],
) -> Subprotocol | None:
    return None


async def _connection_router(websocket: ServerConnection) -> None:
    if websocket.request.path != RUNTIME_PATH:
        await websocket.close(1008, "expected /runtime")
        return
    await _handle_runtime_connection(websocket)


async def _init_shared_model_client() -> None:
    global _shared_model_client
    settings = get_settings()
    try:
        _shared_model_client = build_model_client(settings.provider, **settings.model_kwargs)
    except ModelClientError:
        _shared_model_client = None


async def _shutdown_shared_model_client() -> None:
    global _shared_model_client
    if _shared_model_client is not None and hasattr(_shared_model_client, "close"):
        await _shared_model_client.close()
    _shared_model_client = None
    _run_manager.reset()


async def serve(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    origins: set[str] | None = None,
) -> None:
    await _init_shared_model_client()
    allowed = origins if origins is not None else _allowed_origins()
    origin_hosts = [Origin(origin) for origin in allowed] if allowed else None
    try:
        async with websockets.serve(
            _connection_router,
            host,
            port,
            process_request=_process_request,
            select_subprotocol=_select_subprotocol,
            origins=origin_hosts,
        ):
            print(f"Kgent WebSocket runtime listening on ws://{host}:{port}{RUNTIME_PATH}")
            print(f"Health check: http://{host}:{port}{HEALTH_PATH}")
            await asyncio.Future()
    finally:
        await _shutdown_shared_model_client()


def main() -> None:
    host = os.environ.get("KGENT_WS_HOST", DEFAULT_HOST)
    port = int(os.environ.get("KGENT_WS_PORT", str(DEFAULT_PORT)))
    asyncio.run(serve(host, port))


if __name__ == "__main__":
    main()
