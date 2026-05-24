"""Runtime configuration for Kgent.

Precedence (default `get_settings`):
  environment variables > .env file > built-in defaults

`get_dotenv_settings` (debug CLI):
  .env file > environment variables > built-in defaults
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_ENV_MAP = {
    "KGENT_PROVIDER": "provider",
    "KGENT_MODEL": "model",
    "KGENT_API_KEY": "api_key",
    "KGENT_BASE_URL": "base_url",
    "KGENT_MAX_STEPS": "max_steps",
    "KGENT_PROJECT_ROOT": "project_root",
    "KGENT_MAX_SESSION_MESSAGES": "max_session_messages",
    "KGENT_PERMISSION_MODE": "permission_mode",
    "KGENT_STORAGE_DIR": "storage_dir",
    "KGENT_DISABLE_PERSISTENCE": "disable_persistence",
    "KGENT_TRANSCRIPT_MAX_BYTES": "transcript_max_bytes",
}

_DEFAULTS = {
    "provider": "openai",
    "model": "deepseek-chat",
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "max_steps": 8,
    "project_root": ".",
    "max_session_messages": 100,
    "permission_mode": "risk_based",
    "storage_dir": "",
    "disable_persistence": "0",
    "transcript_max_bytes": 52428800,
}

_VALID_PERMISSION_MODES = ("allow_all", "risk_based", "interactive")


def find_repo_root() -> Path:
    """Locate the Kgent repo root (directory with pyproject.toml or .env)."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    candidates.append(here.parents[3])
    candidates.extend(Path.cwd().parents)
    candidates.append(Path.cwd())

    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "pyproject.toml").exists() or (resolved / ".env").exists():
            return resolved
    return here.parents[3]


def dotenv_path() -> Path:
    return find_repo_root() / ".env"


def _load_dotenv() -> dict[str, str]:
    """Parse .env without mutating os.environ."""
    values: dict[str, str] = {}
    path = dotenv_path()
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values


@dataclass(frozen=True)
class Settings:
    app_name: str = "Kgent"
    provider: str = "openai"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    max_steps: int = 8
    project_root: Path = Path.cwd()
    max_session_messages: int = 100
    permission_mode: str = "risk_based"
    storage_dir: Path = Path(".kgent")
    disable_persistence: bool = False
    transcript_max_bytes: int = 52428800
    dotenv_file: Path | None = None

    @property
    def model_kwargs(self) -> dict[str, object]:
        kw: dict[str, object] = {"model": self.model}
        if self.api_key:
            kw["api_key"] = self.api_key
        if self.base_url:
            kw["base_url"] = self.base_url
        return kw


def _resolve_project_root(raw: str) -> Path:
    if raw in {".", ""}:
        return find_repo_root()
    return Path(raw).resolve()


def _resolve_storage_dir(raw: str, project_root: Path) -> Path:
    if raw in {"", ".kgent"}:
        return (project_root / ".kgent").resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    resolved = candidate.resolve()
    root = project_root.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("KGENT_STORAGE_DIR must stay inside project root")
    return resolved


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _build_settings(dotenv_first: bool) -> Settings:
    dotenv = _load_dotenv()
    env_path = dotenv_path()
    key_by_setting = {setting_key: env_name for env_name, setting_key in _ENV_MAP.items()}

    def _env_value(env_name: str | None) -> str | None:
        if env_name and env_name in os.environ:
            return os.environ[env_name]
        return None

    def _get(key: str) -> str:
        env_name = key_by_setting.get(key)
        if dotenv_first:
            if env_name and env_name in dotenv:
                return dotenv[env_name]
            from_env = _env_value(env_name)
            if from_env is not None:
                return from_env
        else:
            from_env = _env_value(env_name)
            if from_env is not None:
                return from_env
            if env_name and env_name in dotenv:
                return dotenv[env_name]
        return str(_DEFAULTS.get(key, ""))

    provider = _get("provider").lower()
    model = _get("model")
    api_key = _get("api_key")
    base_url = _get("base_url")

    try:
        max_steps = int(_get("max_steps"))
    except (ValueError, TypeError):
        max_steps = _DEFAULTS["max_steps"]
    max_steps = min(max(max_steps, 1), 32)

    try:
        max_session_messages = int(_get("max_session_messages"))
    except (ValueError, TypeError):
        max_session_messages = _DEFAULTS["max_session_messages"]
    max_session_messages = min(max(max_session_messages, 4), 500)

    raw_mode = _get("permission_mode").strip().lower().replace("-", "_")
    permission_mode = raw_mode if raw_mode in _VALID_PERMISSION_MODES else _DEFAULTS["permission_mode"]

    project_root = _resolve_project_root(_get("project_root"))
    storage_dir = _resolve_storage_dir(_get("storage_dir"), project_root)

    try:
        transcript_max_bytes = int(_get("transcript_max_bytes"))
    except (ValueError, TypeError):
        transcript_max_bytes = _DEFAULTS["transcript_max_bytes"]
    transcript_max_bytes = max(transcript_max_bytes, 1024)

    disable_persistence = _parse_bool(_get("disable_persistence"))

    return Settings(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_steps=max_steps,
        project_root=project_root,
        max_session_messages=max_session_messages,
        permission_mode=permission_mode,
        storage_dir=storage_dir,
        disable_persistence=disable_persistence,
        transcript_max_bytes=transcript_max_bytes,
        dotenv_file=env_path if env_path.exists() else None,
    )


@lru_cache
def _cached_settings(dotenv_first: bool) -> Settings:
    return _build_settings(dotenv_first)


def get_settings() -> Settings:
    """Default settings: process env overrides .env."""
    return _cached_settings(False)


def get_dotenv_settings() -> Settings:
    """Debug CLI: .env overrides process env (use your repo .env API key)."""
    return _cached_settings(True)


def reload_settings() -> Settings:
    _cached_settings.cache_clear()
    return get_settings()


def reload_dotenv_settings() -> Settings:
    _cached_settings.cache_clear()
    return get_dotenv_settings()


def mask_secret(value: str) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 10:
        return "***"
    return f"{value[:7]}...{value[-4:]}"
