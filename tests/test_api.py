from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings, reload_settings
from app.main import app


def test_health_lists_providers(monkeypatch) -> None:
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    reload_settings()

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["provider"] == "heuristic"
    assert "heuristic" in data["available_providers"]


def test_chat_api_calculator(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    reload_settings()

    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "帮我算一下 12 * 8 + 6"})

    assert response.status_code == 200
    data = response.json()
    assert "102" in data["answer"]
    assert data["steps"][0]["type"] == "think"
    assert any(step["type"] == "call" and step["tool_name"] == "calculator" for step in data["steps"])
