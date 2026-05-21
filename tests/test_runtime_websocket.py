"""WebSocket runtime API tests (V0.2.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import reload_settings
from app.main import app


def _collect_events(ws, *, until: set[str] | None = None, max_messages: int = 30) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _ in range(max_messages):
        data = ws.receive_json()
        events.append(data)
        if until and data.get("type") in until:
            break
    return events


@pytest.fixture
def ws_client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "interactive")
    reload_settings()
    with TestClient(app) as client:
        yield client


def test_websocket_start_run_finishes_with_risk_based_auto_allow(ws_client: TestClient, monkeypatch) -> None:
    """risk_based allows medium read_file without permission_required."""
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()

    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json({"type": "start_run", "session_id": "ws1", "message": "帮我算一下 12 * 8 + 6"})
        events = _collect_events(ws, until={"run_finished", "run_failed", "error"})

    types = [event["type"] for event in events]
    assert "run_started" in types
    assert "run_finished" in types
    finished = next(event for event in events if event["type"] == "run_finished")
    assert "102" in finished["payload"]["answer"]


def test_websocket_permission_allow(tmp_path: Path, ws_client: TestClient) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n\nA tiny project.", encoding="utf-8")

    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json(
            {"type": "start_run", "session_id": "ws_allow", "message": "请读取 README.md 并总结"}
        )
        events = _collect_events(ws, until={"permission_required", "run_finished", "error"}, max_messages=20)

        perm = next((event for event in events if event["type"] == "permission_required"), None)
        assert perm is not None, f"expected permission_required, got {[e['type'] for e in events]}"
        perm_payload = perm["payload"]["permission_request"]
        run_id = perm["run_id"]

        ws.send_json(
            {
                "type": "permission_decision",
                "run_id": run_id,
                "permission_request_id": perm_payload["permission_request_id"],
                "decision": "allow",
            }
        )
        rest = _collect_events(ws, until={"run_finished", "run_failed", "error"}, max_messages=20)
        events.extend(rest)

    types = [event["type"] for event in events]
    assert "permission_resolved" in types
    assert types.count("permission_resolved") == 1
    assert "tool_call_started" in types
    assert "run_finished" in types
    finished = next(event for event in events if event["type"] == "run_finished")
    assert finished["payload"]["message_count"] >= 4


def test_websocket_permission_deny(tmp_path: Path, ws_client: TestClient) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")

    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json(
            {"type": "start_run", "session_id": "ws_deny", "message": "请读取 README.md"}
        )
        events = _collect_events(ws, until={"permission_required"}, max_messages=20)
        perm = next(event for event in events if event["type"] == "permission_required")
        perm_payload = perm["payload"]["permission_request"]
        run_id = perm["run_id"]

        ws.send_json(
            {
                "type": "permission_decision",
                "run_id": run_id,
                "permission_request_id": perm_payload["permission_request_id"],
                "decision": "deny",
            }
        )
        rest = _collect_events(ws, until={"run_finished", "run_failed"}, max_messages=20)
        events.extend(rest)

    step_events = [
        event["payload"]["step"]
        for event in events
        if event.get("type") == "agent_step" and event.get("payload", {}).get("step", {}).get("type") == "observe"
    ]
    assert any(step.get("is_error") is True for step in step_events)
    assert any(
        str(step.get("content", "")).startswith("permission_denied:")
        for step in step_events
    )


def test_websocket_cancel_waiting_permission(tmp_path: Path, ws_client: TestClient) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")

    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json(
            {"type": "start_run", "session_id": "ws_cancel", "message": "请读取 README.md"}
        )
        events = _collect_events(ws, until={"permission_required"}, max_messages=20)
        perm = next(event for event in events if event["type"] == "permission_required")
        run_id = perm["run_id"]

        ws.send_json({"type": "cancel_run", "run_id": run_id})
        rest = _collect_events(ws, until={"run_cancelled", "run_finished", "error"}, max_messages=10)
        events.extend(rest)

    types = [event["type"] for event in events]
    assert "run_cancelled" in types


def test_websocket_duplicate_permission_decision_returns_error(tmp_path: Path, ws_client: TestClient) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")

    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json(
            {"type": "start_run", "session_id": "ws_dup", "message": "请读取 README.md"}
        )
        events = _collect_events(ws, until={"permission_required"}, max_messages=20)
        perm = next(event for event in events if event["type"] == "permission_required")
        perm_payload = perm["payload"]["permission_request"]
        run_id = perm["run_id"]

        cmd = {
            "type": "permission_decision",
            "run_id": run_id,
            "permission_request_id": perm_payload["permission_request_id"],
            "decision": "allow",
        }
        ws.send_json(cmd)
        ws.send_json(cmd)
        rest = _collect_events(ws, until={"run_finished", "error"}, max_messages=25)
        events.extend(rest)

    error_events = [event for event in events if event.get("type") == "error"]
    assert error_events
    assert any(
        "already resolved" in event["payload"]["error"]
        or "stale permission_request_id" in event["payload"]["error"]
        for event in error_events
    )


def test_websocket_unknown_run_id_returns_error(ws_client: TestClient) -> None:
    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json(
            {
                "type": "permission_decision",
                "run_id": "run_unknown",
                "permission_request_id": "perm_unknown",
                "decision": "allow",
            }
        )
        event = ws.receive_json()

    assert event["type"] == "error"
    assert "unknown run_id" in event["payload"]["error"]


def test_websocket_invalid_command_returns_error(ws_client: TestClient) -> None:
    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_text("{not json")
        event = ws.receive_json()

    assert event["type"] == "error"


def test_websocket_disconnect_does_not_cancel_completed_run(ws_client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()

    with ws_client.websocket_connect("/api/runtime") as ws:
        ws.send_json({"type": "start_run", "session_id": "ws_done", "message": "甯垜绠椾竴涓?12 * 8 + 6"})
        events = _collect_events(ws, until={"run_finished", "run_failed", "error"})
        run_id = next(event["run_id"] for event in events if event["type"] == "run_finished")
        state = app.state.run_manager.get_run(run_id)
        assert state is not None
        assert state.status == "completed"

    state = app.state.run_manager.get_run(run_id)
    assert state is not None
    assert state.status == "completed"
