"""Shared FastAPI dependencies and runtime singletons."""

from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import Settings, get_settings
from app.memory.persistence import PersistenceService, build_persistence_service
from app.model_client import ModelClientProtocol, build_model_client
from app.runtime.permissions import AllowAllPolicy, AskPolicy, PermissionPolicy, RiskBasedPolicy, normalize_mode
from app.runtime.run_manager import RunManager
from app.runtime.todo_state import TodoStateStore
from app.tools.registry import build_tools

_run_manager = RunManager()
_shared_model_client: ModelClientProtocol | None = None
_persistence: PersistenceService | None = None
_todo_state_store = TodoStateStore()


def _ensure_fake_provider_registered() -> None:
    tests_dir = Path(__file__).resolve().parents[3] / "tests"
    tests_path = str(tests_dir)
    if tests_path not in sys.path:
        sys.path.insert(0, tests_path)
    import fake_model  # noqa: F401


def get_run_manager() -> RunManager:
    return _run_manager


def get_todo_state_store() -> TodoStateStore:
    return _todo_state_store


def get_persistence_service() -> PersistenceService:
    global _persistence
    if _persistence is None:
        settings = get_settings()
        _persistence = build_persistence_service(
            storage_dir=settings.storage_dir,
            project_root=settings.project_root,
            transcript_max_bytes=settings.transcript_max_bytes,
            disabled=settings.disable_persistence,
        )
        _run_manager.set_persistence(_persistence)
    return _persistence


def get_app_settings() -> Settings:
    return get_settings()


def build_api_policy(settings: Settings) -> PermissionPolicy:
    mode = normalize_mode(settings.permission_mode)
    if mode == "allow_all":
        return AllowAllPolicy()
    if mode == "interactive":
        return AskPolicy()
    return RiskBasedPolicy()


def resolve_model_client(settings: Settings) -> ModelClientProtocol:
    global _shared_model_client
    if settings.provider == "fake":
        _ensure_fake_provider_registered()
    if _shared_model_client is None:
        _shared_model_client = build_model_client(settings.provider, **settings.model_kwargs)
    return _shared_model_client


async def init_shared_model_client() -> None:
    global _shared_model_client
    settings = get_settings()
    if settings.provider == "fake":
        _ensure_fake_provider_registered()
    try:
        _shared_model_client = build_model_client(settings.provider, **settings.model_kwargs)
    except Exception:
        _shared_model_client = None


async def shutdown_shared_model_client() -> None:
    global _shared_model_client
    if _shared_model_client is not None and hasattr(_shared_model_client, "close"):
        await _shared_model_client.close()
    _shared_model_client = None
    _run_manager.reset()
    _todo_state_store.reset()
    global _persistence
    _persistence = None


def build_runtime_tools(
    settings: Settings,
    *,
    session_id: str = "default",
    persistence: PersistenceService | None = None,
    todo_state_store: TodoStateStore | None = None,
):
    from app.tools.registry import build_subagent_runner

    model_client = resolve_model_client(settings)
    policy = build_api_policy(settings)

    subagent_runner = build_subagent_runner(
        model_client=model_client,
        parent_session_id=session_id,
        project_root=settings.project_root,
        policy=policy,
        persistence=persistence,
        todo_state_store=todo_state_store,
    )

    return build_tools(
        settings.project_root,
        session_id=session_id,
        persistence=persistence,
        todo_state_store=todo_state_store,
        subagent_runner=subagent_runner,
        include_task_tool=True,
    )
