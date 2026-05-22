"""FastAPI/ASGI entrypoint for Kgent HTTP + SSE runtime (V0.2.2)."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import get_app_settings, init_shared_model_client, shutdown_shared_model_client
from app.api.router import api_router
from app.model_client import available_providers
from app.tools.registry import build_tools

_DEFAULT_DEV_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://127.0.0.1:5173",
    "https://localhost:5173",
]


def _cors_origins() -> list[str]:
    raw = os.environ.get("KGENT_CORS_ORIGINS", "")
    if not raw.strip():
        return list(_DEFAULT_DEV_ORIGINS)
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _cors_allow_credentials(origins: list[str]) -> bool:
    return "*" not in origins


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_shared_model_client()
    yield
    await shutdown_shared_model_client()


app = FastAPI(title="Kgent Runtime", lifespan=lifespan)

_cors = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=_cors_allow_credentials(_cors),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    settings = get_app_settings()
    from app.api.deps import _shared_model_client

    tool_risks = {
        tool.name: getattr(tool, "risk_level", "high")
        for tool in build_tools(settings.project_root)
    }
    return {
        "status": "ok",
        "provider": settings.provider,
        "available_providers": available_providers(),
        "model_client_ready": _shared_model_client is not None,
        "permission_mode": settings.permission_mode,
        "effective_permission_mode": settings.permission_mode,
        "tool_risks": tool_risks,
    }
