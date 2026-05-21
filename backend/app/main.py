"""FastAPI entrypoint for Kgent."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.model_client import ModelClientError, ModelClientProtocol, build_model_client
from app.api.chat import resolve_api_permission_mode, router as chat_router
from app.api.runtime import router as runtime_router
from app.runtime.run_manager import RunManager
from app.core.config import get_settings
from app.tools.registry import build_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    model_client: ModelClientProtocol | None = None
    try:
        model_client = build_model_client(settings.provider, **settings.model_kwargs)
    except ModelClientError:
        model_client = None
    app.state.model_client = model_client
    app.state.run_manager = RunManager()
    yield
    if model_client is not None and hasattr(model_client, "close"):
        await model_client.close()
    run_manager: RunManager = app.state.run_manager
    run_manager.reset()


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, object]:
    from app.model_client import available_providers

    current = get_settings()
    effective_mode = resolve_api_permission_mode(current.permission_mode)
    tool_risks = {
        tool.name: getattr(tool, "risk_level", "high")
        for tool in build_tools(current.project_root)
    }
    return {
        "status": "ok",
        "provider": current.provider,
        "available_providers": available_providers(),
        "model_client_ready": getattr(app.state, "model_client", None) is not None,
        "permission_mode": current.permission_mode,
        "effective_permission_mode": effective_mode,
        "tool_risks": tool_risks,
    }


app.include_router(chat_router)
app.include_router(runtime_router)
