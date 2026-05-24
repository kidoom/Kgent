"""SSE event stream for session-scoped AgentEvent delivery.

Access control is session_id only (no auth). Suitable for local dev; production
deployments should use unguessable session ids (see POST /api/sessions) and/or auth.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_run_manager
from app.api.errors import api_error
from app.memory.session_id import validate_session_id
from app.runtime.protocol import AgentEvent, heartbeat_event
from app.runtime.run_manager import RunManager

router = APIRouter()

HEARTBEAT_INTERVAL_SEC = 15.0
SSE_CONNECTED_PREAMBLE = ": connected\n\n"


def _format_sse(event: AgentEvent) -> str:
    payload = event.model_dump(mode="json")
    return f"id: {event.seq}\nevent: agent_event\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _parse_from_seq(request: Request, from_seq: int | None) -> int:
    if from_seq is not None:
        return max(from_seq, 0)
    last_event_id = request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")
    if last_event_id:
        try:
            return max(int(last_event_id), 0)
        except ValueError:
            return 0
    return 0


async def _session_event_stream(
    *,
    session_id: str,
    after_seq: int,
    run_manager: RunManager,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue()

    async def subscriber(event: AgentEvent) -> None:
        await queue.put(event)

    run_manager.subscribe_session(session_id, subscriber)
    try:
        # Flush headers/body immediately so dev proxies and EventSource can mark
        # the connection open even when there are no replayable events yet.
        yield SSE_CONNECTED_PREAMBLE
        for event in run_manager.get_session_events_after(session_id, after_seq):
            yield _format_sse(event)

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL_SEC)
            except asyncio.TimeoutError:
                heartbeat = await run_manager.publish_session_event(
                    heartbeat_event(session_id=session_id, seq=0),
                    store=False,
                )
                yield _format_sse(heartbeat)
                continue

            if event is None:
                break
            yield _format_sse(event)
    finally:
        run_manager.unsubscribe_session(session_id, subscriber)


@router.get("/sessions/{session_id}/events")
async def session_events(
    session_id: str,
    request: Request,
    from_seq: int | None = None,
    run_manager: RunManager = Depends(get_run_manager),
) -> StreamingResponse:
    try:
        validate_session_id(session_id)
    except ValueError as exc:
        raise api_error(400, error_type="validation_error", message=str(exc)) from exc

    after_seq = _parse_from_seq(request, from_seq)

    return StreamingResponse(
        _session_event_stream(
            session_id=session_id,
            after_seq=after_seq,
            run_manager=run_manager,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
