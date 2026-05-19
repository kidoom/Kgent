import pytest

from app.agent.session_store import reset_sessions
from app.core.config import reload_settings


@pytest.fixture(autouse=True)
def _isolate_sessions() -> None:
    reset_sessions()
    yield
    reset_sessions()


@pytest.fixture(autouse=True)
def _offline_test_config(monkeypatch) -> None:
    """Keep tests offline: repo .env must not override heuristic in pytest."""
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    monkeypatch.setenv("KGENT_API_KEY", "")
    reload_settings()
