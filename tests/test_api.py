from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_chat_api_calculator(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    get_settings.cache_clear()

    client = TestClient(app)
    response = client.post("/api/chat", json={"message": "帮我算一下 12 * 8 + 6"})

    assert response.status_code == 200
    data = response.json()
    assert "102" in data["answer"]
    assert data["steps"][0]["type"] == "tool_use"
