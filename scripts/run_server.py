#!/usr/bin/env python3
"""Run the Kgent FastAPI server; reads KGENT_SSL_* and host/port from .env or env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.core.config import _load_dotenv  # noqa: E402


def _env(name: str, default: str = "") -> str:
    if name in os.environ:
        return os.environ[name]
    return _load_dotenv().get(name, default)


def _parse_bool(raw: str, default: bool = False) -> bool:
    if not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(raw: str, default: int) -> int:
    if not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def main() -> None:
    import uvicorn

    host = _env("KGENT_HOST", "127.0.0.1")
    port = _parse_int(_env("KGENT_PORT", "8000"), 8000)
    reload = _parse_bool(_env("KGENT_RELOAD", ""), default=False)

    ssl_keyfile = _env("KGENT_SSL_KEYFILE", "").strip()
    ssl_certfile = _env("KGENT_SSL_CERTFILE", "").strip()

    kwargs: dict[str, object] = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "reload": reload,
    }

    if ssl_keyfile and ssl_certfile:
        kwargs["ssl_keyfile"] = ssl_keyfile
        kwargs["ssl_certfile"] = ssl_certfile
    elif ssl_keyfile or ssl_certfile:
        print(
            "Warning: both KGENT_SSL_KEYFILE and KGENT_SSL_CERTFILE are required for TLS; "
            "starting without SSL.",
            file=sys.stderr,
        )

    uvicorn.run(**kwargs)


if __name__ == "__main__":
    main()
