"""Test 4-step multi-turn scenario that freezes the frontend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import websockets

from app.core.config import reload_settings
from app.memory.session_store import reset_sessions
from app.transport.ws_server import RUNTIME_PATH, get_run_manager


async def _collect_events(
    ws,
    *,
    until: set[str] | None = None,
    max_messages: int = 50,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _ in range(max_messages):
        raw = await ws.recv()
        data = json.loads(raw)
        events.append(data)
        if until and data.get("type") in until:
            break
    return events


async def _send_and_finish(
    ws,
    session_id: str,
    message: str,
    *,
    allow_perm: bool = False,
) -> list[dict[str, Any]]:
    await ws.send(
        json.dumps(
            {"type": "start_run", "session_id": session_id, "message": message},
            ensure_ascii=False,
        )
    )
    events = await _collect_events(
        ws,
        until={"permission_required", "run_finished", "run_failed", "error", "run_cancelled"},
    )
    if allow_perm and any(event["type"] == "permission_required" for event in events):
        perm = next(event for event in events if event["type"] == "permission_required")
        req = perm["payload"]["permission_request"]
        await ws.send(
            json.dumps(
                {
                    "type": "permission_decision",
                    "run_id": perm["run_id"],
                    "permission_request_id": req["permission_request_id"],
                    "decision": "allow",
                }
            )
        )
        rest = await _collect_events(
            ws,
            until={"run_finished", "run_failed", "error", "run_cancelled"},
        )
        events.extend(rest)
    return events


@pytest.fixture
async def ws_server_url(tmp_path: Path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n\nA tiny agent project for testing.", encoding="utf-8")

    monkeypatch.setenv("KGENT_PROVIDER", "fake")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "interactive")
    reload_settings()

    get_run_manager().reset()
    reset_sessions()

    host = "127.0.0.1"
    from app.transport import ws_server as ws_mod

    async with websockets.serve(
        ws_mod._connection_router,
        host,
        0,
        process_request=ws_mod._process_request,
        origins=None,
    ) as server:
        await ws_mod._init_shared_model_client()
        port = server.sockets[0].getsockname()[1]
        url = f"ws://{host}:{port}{RUNTIME_PATH}"
        try:
            yield url
        finally:
            await ws_mod._shutdown_shared_model_client()


@pytest.mark.asyncio
async def test_websocket_four_turn_repro_sequence(ws_server_url: str) -> None:
    """Repro: hello -> calc -> read README -> summarize what was read."""
    session_id = "web-default"
    async with websockets.connect(ws_server_url) as ws:
        events1 = await _send_and_finish(ws, session_id, "你好")
        assert any(event["type"] == "run_finished" for event in events1)

        events2 = await _send_and_finish(ws, session_id, "计算8+8")
        assert any(event["type"] == "run_finished" for event in events2)
        finished2 = next(event for event in events2 if event["type"] == "run_finished")
        assert "16" in finished2["payload"]["answer"]

        events3 = await _send_and_finish(ws, session_id, "阅读 README.md", allow_perm=True)
        assert any(event["type"] == "run_finished" for event in events3)

        events4 = await _send_and_finish(ws, session_id, "总结一下刚刚读的内容")
        types4 = [event["type"] for event in events4]
        assert "run_finished" in types4, f"step 4 stuck: {types4}"
        finished4 = next(event for event in events4 if event["type"] == "run_finished")
        answer = finished4["payload"]["answer"]
        assert answer, "step 4 should have a non-empty answer"
        assert "Demo" in answer or "Kgent" in answer or "agent" in answer.lower()
