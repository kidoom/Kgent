"""Runtime configuration for Kgent.

Precedence: environment variables > .env file > built-in defaults.
Default provider is "heuristic" so tests and offline use work out of the box.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DOTENV_FILE = _PROJECT_ROOT / ".env"


def _load_dotenv() -> dict[str, str]:
    """Parse .env without mutating os.environ."""
    values: dict[str, str] = {}
    if not _DOTENV_FILE.exists():
        return values
    for line in _DOTENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values

_DEFAULTS = {
    "provider": "heuristic",
    "model": "deepseek-chat",
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "max_steps": 8,
    "project_root": ".",
    "cors_origins": "http://localhost:3000,http://localhost:5173",
}

# Env var names for each supported setting.
_ENV_MAP = {
    "KGENT_PROVIDER": "provider",
    "KGENT_MODEL": "model",
    "KGENT_API_KEY": "api_key",
    "KGENT_BASE_URL": "base_url",
    "KGENT_MAX_STEPS": "max_steps",
    "KGENT_PROJECT_ROOT": "project_root",
    "KGENT_CORS_ORIGINS": "cors_origins",
}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Kgent"
    provider: str = "heuristic"
    model: str = "deepseek-chat"
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    max_steps: int = 8
    project_root: Path = Path.cwd()
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def model_kwargs(self) -> dict[str, object]:
        """Extra kwargs forwarded to the model client constructor."""
        kw: dict[str, object] = {"model": self.model}
        if self.api_key:
            kw["api_key"] = self.api_key
        if self.base_url:
            kw["base_url"] = self.base_url
        return kw


@lru_cache
def get_settings() -> Settings:
    dotenv = _load_dotenv()
    key_by_setting = {setting_key: env_name for env_name, setting_key in _ENV_MAP.items()}

    def _get(key: str) -> str:
        """Return env var if set, else .env, else default. Never returns None."""
        env_name = key_by_setting.get(key)
        if env_name and env_name in os.environ:
            return os.environ[env_name]
        if env_name and env_name in dotenv:
            return dotenv[env_name]
        return str(_DEFAULTS.get(key, ""))

    provider = _get("provider").lower()
    model = _get("model")
    api_key = _get("api_key")
    base_url = _get("base_url")
    cors_origins = _get("cors_origins")

    try:
        max_steps = int(_get("max_steps"))
    except (ValueError, TypeError):
        max_steps = _DEFAULTS["max_steps"]
    max_steps = min(max(max_steps, 1), 32)

    project_root = Path(str(_get("project_root"))).resolve()

    return Settings(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_steps=max_steps,
        project_root=project_root,
        cors_origins=cors_origins,
    )


def reload_settings() -> Settings:
    """Clear the cache and reload from disk."""
    get_settings.cache_clear()
    return get_settings()
