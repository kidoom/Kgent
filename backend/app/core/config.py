"""Runtime configuration for Kgent."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings.

    V0.1 defaults to a deterministic local model client so the loop is runnable
    without network access or API keys.
    """

    app_name: str = "Kgent"
    max_steps: int = 8
    project_root: Path = Path.cwd()
    model_client: Literal["heuristic", "openai"] = "heuristic"
    openai_model: str = "gpt-4.1-mini"


@lru_cache
def get_settings() -> Settings:
    client = os.environ.get("KGENT_MODEL_CLIENT", "heuristic").lower()
    if client not in {"heuristic", "openai"}:
        client = "heuristic"

    raw_max_steps = os.environ.get("KGENT_MAX_STEPS", "8")
    try:
        max_steps = int(raw_max_steps)
    except ValueError:
        max_steps = 8
    max_steps = min(max(max_steps, 1), 32)

    project_root = Path(os.environ.get("KGENT_PROJECT_ROOT", Path.cwd())).resolve()

    return Settings(
        max_steps=max_steps,
        project_root=project_root,
        model_client=cast(Literal["heuristic", "openai"], client),
        openai_model=os.environ.get("KGENT_OPENAI_MODEL", "gpt-4.1-mini"),
    )
