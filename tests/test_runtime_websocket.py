"""WebSocket runtime server tests (standalone websockets transport)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import websockets

from app.core.config import reload_settings
from app.transport.ws_server import RUNTIME_PATH, get_run_manager


async def _collect_events(
    ws,
    *,
    until: set[str] | None = None,
    max_messages: int = 30,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _ in range(max_messages):
        raw = await ws.recv()
        data = json.loads(raw)
        events.append(data)
        if until and data.get("type") in until:
            break
    return events


@pytest.fixture
async def ws_server_url(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KGENT_PROVIDER", "fake")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "interactive")
    reload_settings()

    get_run_manager().reset()

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
async def test_websocket_start_run_finishes_with_risk_based_auto_allow(
    ws_server_url: str,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()

    async with websockets.connect(ws_server_url) as ws:
        await ws.send(json.dumps({"type": "start_run", "session_id": "ws1", "message": "帮我算一下 12 * 8 + 6"}))
        events = await _collect_events(ws, until={"run_finished", "run_failed", "error"})

    types = [event["type"] for event in events]
    assert "run_started" in types
    assert "run_finished" in types
    finished = next(event for event in events if event["type"] == "run_finished")
    assert "102" in finished["payload"]["answer"]


@pytest.mark.asyncio
async def test_websocket_permission_allow(ws_server_url: str, tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n\nA tiny project.", encoding="utf-8")

    async with websockets.connect(ws_server_url) as ws:
        await ws.send(
            json.dumps({"type": "start_run", "session_id": "ws_allow", "message": "请读取 README.md 并总结"})
        )
        events = await _collect_events(
            ws, until={"permission_required", "run_finished", "error"}, max_messages=20
        )

        perm = next((event for event in events if event["type"] == "permission_required"), None)
        assert perm is not None, f"expected permission_required, got {[e['type'] for e in events]}"
        perm_payload = perm["payload"]["permission_request"]
        run_id = perm["run_id"]

        await ws.send(
            json.dumps(
                {
                    "type": "permission_decision",
                    "run_id": run_id,
                    "permission_request_id": perm_payload["permission_request_id"],
                    "decision": "allow",
                }
            )
        )
        rest = await _collect_events(ws, until={"run_finished", "run_failed", "error"}, max_messages=20)
        events.extend(rest)

    types = [event["type"] for event in events]
    assert "permission_resolved" in types
    assert types.count("permission_resolved") == 1
    assert "tool_call_started" in types
    assert "run_finished" in types


@pytest.mark.asyncio
async def test_websocket_permission_deny(ws_server_url: str, tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")

    async with websockets.connect(ws_server_url) as ws:
        await ws.send(json.dumps({"type": "start_run", "session_id": "ws_deny", "message": "请读取 README.md"}))
        events = await _collect_events(ws, until={"permission_required"}, max_messages=20)
        perm = next(event for event in events if event["type"] == "permission_required")
        perm_payload = perm["payload"]["permission_request"]
        run_id = perm["run_id"]

        await ws.send(
            json.dumps(
                {
                    "type": "permission_decision",
                    "run_id": run_id,
                    "permission_request_id": perm_payload["permission_request_id"],
                    "decision": "deny",
                }
            )
        )
        rest = await _collect_events(ws, until={"run_finished", "run_failed"}, max_messages=20)
        events.extend(rest)

    step_events = [
        event["payload"]["step"]
        for event in events
        if event.get("type") == "agent_step" and event.get("payload", {}).get("step", {}).get("type") == "observe"
    ]
    assert any(step.get("is_error") is True for step in step_events)
    assert any(str(step.get("content", "")).startswith("permission_denied:") for step in step_events)


@pytest.mark.asyncio
async def test_websocket_cancel_waiting_permission(ws_server_url: str, tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")

    async with websockets.connect(ws_server_url) as ws:
        await ws.send(json.dumps({"type": "start_run", "session_id": "ws_cancel", "message": "请读取 README.md"}))
        events = await _collect_events(ws, until={"permission_required"}, max_messages=20)
        perm = next(event for event in events if event["type"] == "permission_required")
        run_id = perm["run_id"]

        await ws.send(json.dumps({"type": "cancel_run", "run_id": run_id}))
        rest = await _collect_events(ws, until={"run_cancelled", "run_finished", "error"}, max_messages=10)
        events.extend(rest)

    types = [event["type"] for event in events]
    assert "run_cancelled" in types


@pytest.mark.asyncio
async def test_websocket_duplicate_permission_decision_returns_error(
    ws_server_url: str, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")

    async with websockets.connect(ws_server_url) as ws:
        await ws.send(json.dumps({"type": "start_run", "session_id": "ws_dup", "message": "请读取 README.md"}))
        events = await _collect_events(ws, until={"permission_required"}, max_messages=20)
        perm = next(event for event in events if event["type"] == "permission_required")
        perm_payload = perm["payload"]["permission_request"]
        run_id = perm["run_id"]

        cmd = {
            "type": "permission_decision",
            "run_id": run_id,
            "permission_request_id": perm_payload["permission_request_id"],
            "decision": "allow",
        }
        await ws.send(json.dumps(cmd))
        await ws.send(json.dumps(cmd))
        rest = await _collect_events(ws, until={"run_finished", "error"}, max_messages=25)
        events.extend(rest)

    error_events = [event for event in events if event.get("type") == "error"]
    assert error_events
    assert any(
        "already resolved" in event["payload"]["error"]
        or "stale permission_request_id" in event["payload"]["error"]
        for event in error_events
    )


@pytest.mark.asyncio
async def test_websocket_unknown_run_id_returns_error(ws_server_url: str) -> None:
    async with websockets.connect(ws_server_url) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "permission_decision",
                    "run_id": "run_unknown",
                    "permission_request_id": "perm_unknown",
                    "decision": "allow",
                }
            )
        )
        raw = await ws.recv()
        event = json.loads(raw)

    assert event["type"] == "error"
    assert "unknown run_id" in event["payload"]["error"]


@pytest.mark.asyncio
async def test_websocket_invalid_command_returns_error(ws_server_url: str) -> None:
    async with websockets.connect(ws_server_url) as ws:
        await ws.send("{not json")
        raw = await ws.recv()
        event = json.loads(raw)

    assert event["type"] == "error"


@pytest.mark.asyncio
async def test_websocket_disconnect_does_not_cancel_completed_run(
    ws_server_url: str, monkeypatch
) -> None:
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()

    run_id = ""
    async with websockets.connect(ws_server_url) as ws:
        await ws.send(json.dumps({"type": "start_run", "session_id": "ws_done", "message": "帮我算一下 12 * 8 + 6"}))
        events = await _collect_events(ws, until={"run_finished", "run_failed", "error"})
        run_id = next(event["run_id"] for event in events if event["type"] == "run_finished")
        state = get_run_manager().get_run(run_id)
        assert state is not None
        assert state.status == "completed"

    state = get_run_manager().get_run(run_id)
    assert state is not None
    assert state.status == "completed"


@pytest.mark.asyncio
async def test_websocket_multiple_sequential_runs(ws_server_url: str) -> None:
    async with websockets.connect(ws_server_url) as ws:
        for i in range(3):
            await ws.send(
                json.dumps(
                    {
                        "type": "start_run",
                        "session_id": "ws_multi",
                        "message": f"calculate {i + 1} + {i + 1}",
                    }
                )
            )
            events = await _collect_events(ws, until={"run_finished", "run_failed", "error"})
            assert any(event["type"] == "run_finished" for event in events), events
            finished = next(event for event in events if event["type"] == "run_finished")
            assert str((i + 1) * 2) in finished["payload"]["answer"]
