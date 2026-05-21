import sys
from pathlib import Path

import pytest

from app.memory.session_store import reset_sessions
from app.core.config import reload_settings

_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import fake_model  # noqa: F401, E402 — registers "fake" provider for offline tests


@pytest.fixture(autouse=True)
def _isolate_sessions() -> None:
    reset_sessions()
    yield
    reset_sessions()


@pytest.fixture(autouse=True)
def _offline_test_config(monkeypatch) -> None:
    """Keep tests offline: use fake provider, ignore repo .env API settings."""
    monkeypatch.setenv("KGENT_PROVIDER", "fake")
    monkeypatch.setenv("KGENT_API_KEY", "")
    monkeypatch.setenv("KGENT_PERMISSION_MODE", "risk_based")
    reload_settings()
