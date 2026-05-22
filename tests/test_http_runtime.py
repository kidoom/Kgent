"""HTTP + SSE runtime API tests (V0.2.2)."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

import fake_model  # noqa: F401 — registers fake provider

from app.core.config import reload_settings

_REPO_ROOT = Path(__file__).resolve().parents[1]


async def _sse_event_queue(response: httpx.Response) -> asyncio.Queue[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def _reader() -> None:
        buffer = ""
        try:
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    block, buffer = buffer.split("\n\n", 1)
                    data_line = next((line for line in block.splitlines() if line.startswith("data:")), None)
                    if data_line is None:
                        continue
                    payload = json.loads(data_line.removeprefix("data:").strip())
                    if payload.get("type") == "heartbeat":
                        continue
                    await queue.put(payload)
        finally:
            await queue.put({"type": "__stream_closed__"})

    asyncio.create_task(_reader())
    return queue


async def _collect_until(
    queue: asyncio.Queue[dict[str, Any]],
    *,
    until: set[str],
    max_events: int = 40,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    while len(events) < max_events:
        event = await queue.get()
        if event.get("type") == "__stream_closed__":
            break
        events.append(event)
        if event.get("type") in until:
            break
    return events


async def _parse_sse_stream(
    response: httpx.Response,
    *,
    until: set[str] | None = None,
    max_events: int = 40,
) -> list[dict[str, Any]]:
    queue = await _sse_event_queue(response)
    if until:
        return await _collect_until(queue, until=until, max_events=max_events)
    events: list[dict[str, Any]] = []
    while len(events) < max_events:
        event = await queue.get()
        if event.get("type") == "__stream_closed__":
            break
        events.append(event)
    return events


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def server_project_root(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("http_runtime")


@pytest.fixture(scope="session")
def live_server_url(server_project_root: Path) -> str:
    port = _free_port()
    env = os.environ.copy()
    env["KGENT_PROVIDER"] = "fake"
    env["KGENT_PROJECT_ROOT"] = str(server_project_root)
    env["KGENT_PERMISSION_MODE"] = "interactive"
    env["PYTHONPATH"] = str(_REPO_ROOT / "backend") + os.pathsep + str(_REPO_ROOT / "tests")

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while time.time() < deadline:
        if proc.poll() is not None:
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            raise RuntimeError(f"uvicorn exited early:\n{stderr}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("uvicorn did not start in time")

    yield url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
async def api_client(live_server_url: str):
    async with httpx.AsyncClient(base_url=live_server_url, timeout=30.0, trust_env=False) as client:
        yield client


def _make_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url, timeout=30.0, trust_env=False)


async def _run_with_sse(
    base_url: str,
    *,
    session_id: str,
    message: str | None = None,
    until: set[str] | None = None,
    max_events: int = 40,
) -> tuple[list[dict[str, Any]], httpx.Response | None]:
    async with _make_client(base_url) as sse_client, _make_client(base_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            post_response: httpx.Response | None = None
            if message is not None:
                post_task = asyncio.create_task(
                    cmd_client.post(
                        f"/api/sessions/{session_id}/messages",
                        json={"message": message},
                    )
                )
                events = await _parse_sse_stream(sse, until=until, max_events=max_events)
                post_response = await post_task
                return events, post_response
            events = await _parse_sse_stream(sse, until=until, max_events=max_events)
            return events, post_response


@pytest.mark.asyncio
async def test_health(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "tool_risks" in body


@pytest.mark.asyncio
async def test_http_start_run_finishes_with_risk_based_auto_allow(
    live_server_url: str,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()
    session_id = "http_risk"

    events, response = await _run_with_sse(
        live_server_url,
        session_id=session_id,
        message="帮我算一下 12 * 8 + 6",
        until={"run_finished", "run_failed", "error"},
    )

    assert response is not None
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert "answer" not in body

    types = [event["type"] for event in events]
    assert "run_started" in types
    assert "run_finished" in types
    finished = next(event for event in events if event["type"] == "run_finished")
    assert "102" in finished["payload"]["answer"]


@pytest.mark.asyncio
async def test_http_permission_allow(live_server_url: str, server_project_root: Path) -> None:
    readme = server_project_root / "README.md"
    readme.write_text("# Demo\n\nA tiny project.", encoding="utf-8")
    session_id = "http_allow"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            queue = await _sse_event_queue(sse)
            post_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "请读取 README.md 并总结"},
                )
            )
            events = await _collect_until(queue, until={"permission_required"}, max_events=25)
            post_response = await post_task
            assert post_response.status_code == 200
            run_id = post_response.json()["run_id"]

            perm = next(event for event in events if event["type"] == "permission_required")
            perm_payload = perm["payload"]["permission_request"]

            decision = await cmd_client.post(
                f"/api/runs/{run_id}/permission",
                json={
                    "permission_request_id": perm_payload["permission_request_id"],
                    "decision": "allow",
                },
            )
            assert decision.status_code == 200

            events.extend(
                await _collect_until(queue, until={"run_finished", "run_failed", "error"}, max_events=25)
            )

    types = [event["type"] for event in events]
    assert "permission_resolved" in types
    assert "run_finished" in types


@pytest.mark.asyncio
async def test_http_permission_deny(live_server_url: str, server_project_root: Path) -> None:
    readme = server_project_root / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")
    session_id = "http_deny"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            queue = await _sse_event_queue(sse)
            post_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "请读取 README.md"},
                )
            )
            events = await _collect_until(queue, until={"permission_required"}, max_events=25)
            post_response = await post_task
            run_id = post_response.json()["run_id"]
            perm = next(event for event in events if event["type"] == "permission_required")
            perm_payload = perm["payload"]["permission_request"]

            await cmd_client.post(
                f"/api/runs/{run_id}/permission",
                json={
                    "permission_request_id": perm_payload["permission_request_id"],
                    "decision": "deny",
                },
            )
            events.extend(await _collect_until(queue, until={"run_finished", "run_failed"}, max_events=25))

    step_events = [
        event["payload"]["step"]
        for event in events
        if event.get("type") == "agent_step" and event.get("payload", {}).get("step", {}).get("type") == "observe"
    ]
    assert any(step.get("is_error") is True for step in step_events)
    assert any(str(step.get("content", "")).startswith("permission_denied:") for step in step_events)


@pytest.mark.asyncio
async def test_http_write_file_permission_allow_mutates_file(
    live_server_url: str,
    server_project_root: Path,
) -> None:
    target = server_project_root / "agent-note.txt"
    target.unlink(missing_ok=True)
    session_id = "http_write_allow"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            queue = await _sse_event_queue(sse)
            post_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "write_file path=agent-note.txt content=approved write"},
                )
            )
            events = await _collect_until(queue, until={"permission_required"}, max_events=25)
            post_response = await post_task
            assert post_response.status_code == 200
            run_id = post_response.json()["run_id"]

            perm = next(event for event in events if event["type"] == "permission_required")
            perm_payload = perm["payload"]["permission_request"]
            assert perm_payload["tool_name"] == "write_file"
            assert perm_payload["risk_level"] == "high"
            assert perm_payload["tool_input"] == {
                "path": "agent-note.txt",
                "content": "approved write",
            }

            decision = await cmd_client.post(
                f"/api/runs/{run_id}/permission",
                json={
                    "permission_request_id": perm_payload["permission_request_id"],
                    "decision": "allow",
                },
            )
            assert decision.status_code == 200
            events.extend(await _collect_until(queue, until={"run_finished", "run_failed"}, max_events=25))

    assert target.read_text(encoding="utf-8") == "approved write"
    observe_steps = [
        event["payload"]["step"]
        for event in events
        if event.get("type") == "agent_step" and event.get("payload", {}).get("step", {}).get("type") == "observe"
    ]
    assert any(step.get("is_error") is False and "written: agent-note.txt" in step.get("content", "") for step in observe_steps)
    assert any(event["type"] == "permission_resolved" for event in events)
    assert any(event["type"] == "run_finished" for event in events)


@pytest.mark.asyncio
async def test_http_write_file_permission_deny_does_not_mutate_file(
    live_server_url: str,
    server_project_root: Path,
) -> None:
    target = server_project_root / "denied-note.txt"
    target.unlink(missing_ok=True)
    session_id = "http_write_deny"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            queue = await _sse_event_queue(sse)
            post_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "write_file path=denied-note.txt content=should not persist"},
                )
            )
            events = await _collect_until(queue, until={"permission_required"}, max_events=25)
            post_response = await post_task
            assert post_response.status_code == 200
            run_id = post_response.json()["run_id"]
            perm_payload = next(event for event in events if event["type"] == "permission_required")["payload"][
                "permission_request"
            ]

            decision = await cmd_client.post(
                f"/api/runs/{run_id}/permission",
                json={
                    "permission_request_id": perm_payload["permission_request_id"],
                    "decision": "deny",
                },
            )
            assert decision.status_code == 200
            events.extend(await _collect_until(queue, until={"run_finished", "run_failed"}, max_events=25))

    assert not target.exists()
    observe_steps = [
        event["payload"]["step"]
        for event in events
        if event.get("type") == "agent_step" and event.get("payload", {}).get("step", {}).get("type") == "observe"
    ]
    assert any(step.get("is_error") is True for step in observe_steps)
    assert any(str(step.get("content", "")).startswith("permission_denied:") for step in observe_steps)

@pytest.mark.asyncio
async def test_http_cancel_waiting_permission(live_server_url: str, server_project_root: Path) -> None:
    readme = server_project_root / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")
    session_id = "http_cancel"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            queue = await _sse_event_queue(sse)
            post_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "请读取 README.md"},
                )
            )
            events = await _collect_until(queue, until={"permission_required"}, max_events=25)
            post_response = await post_task
            run_id = post_response.json()["run_id"]

            cancel = await cmd_client.post(f"/api/runs/{run_id}/cancel", json={})
            assert cancel.status_code == 200
            events.extend(
                await _collect_until(queue, until={"run_cancelled", "run_finished", "error"}, max_events=15)
            )

    types = [event["type"] for event in events]
    assert "run_cancelled" in types


@pytest.mark.asyncio
async def test_http_duplicate_permission_decision_returns_409(
    live_server_url: str,
    server_project_root: Path,
) -> None:
    readme = server_project_root / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")
    session_id = "http_dup"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            post_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "请读取 README.md"},
                )
            )
            events = await _parse_sse_stream(sse, until={"permission_required"}, max_events=25)
            post_response = await post_task
            run_id = post_response.json()["run_id"]
            perm_payload = next(event for event in events if event["type"] == "permission_required")[
                "payload"
            ]["permission_request"]

            payload = {
                "permission_request_id": perm_payload["permission_request_id"],
                "decision": "allow",
            }
            first = await cmd_client.post(f"/api/runs/{run_id}/permission", json=payload)
            second = await cmd_client.post(f"/api/runs/{run_id}/permission", json=payload)
            assert first.status_code == 200
            assert second.status_code == 409


@pytest.mark.asyncio
async def test_http_active_run_conflict(live_server_url: str, server_project_root: Path) -> None:
    readme = server_project_root / "README.md"
    readme.write_text("# Demo\n", encoding="utf-8")
    session_id = "http_conflict"

    async with _make_client(live_server_url) as sse_client, _make_client(live_server_url) as cmd_client:
        async with sse_client.stream("GET", f"/api/sessions/{session_id}/events") as sse:
            queue = await _sse_event_queue(sse)
            first_task = asyncio.create_task(
                cmd_client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"message": "请读取 README.md"},
                )
            )
            await _collect_until(queue, until={"permission_required"}, max_events=25)
            first = await first_task
            second = await cmd_client.post(
                f"/api/sessions/{session_id}/messages",
                json={"message": "another message"},
            )

    statuses = {first.status_code, second.status_code}
    assert first.status_code == 200
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_sse_reconnect_replays_from_seq(live_server_url: str, monkeypatch) -> None:
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()
    session_id = "http_reconnect"

    events, _ = await _run_with_sse(
        live_server_url,
        session_id=session_id,
        message="帮我算一下 2 + 2",
        until={"run_finished"},
    )
    last_seq = max(event["seq"] for event in events)

    async with _make_client(live_server_url) as sse_client:
        async with sse_client.stream(
            "GET",
            f"/api/sessions/{session_id}/events",
            params={"from_seq": last_seq},
        ) as sse:
            queue = await _sse_event_queue(sse)
            replay: list[dict[str, Any]] = []
            try:
                async def _drain() -> None:
                    while len(replay) < 5:
                        event = await queue.get()
                        if event.get("type") == "__stream_closed__":
                            break
                        replay.append(event)

                await asyncio.wait_for(_drain(), timeout=3)
            except asyncio.TimeoutError:
                pass

    assert all(event["seq"] > last_seq for event in replay)
