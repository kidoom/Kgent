"""FastAPI entrypoint for Kgent."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.model_client import ModelClientError, ModelClientProtocol, build_model_client
from app.api.chat import router as chat_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    model_client: ModelClientProtocol | None = None
    try:
        model_client = build_model_client(settings.provider, **settings.model_kwargs)
    except ModelClientError:
        model_client = None
    app.state.model_client = model_client
    yield
    if model_client is not None and hasattr(model_client, "close"):
        await model_client.close()


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
    from app.agent.model_client import available_providers

    current = get_settings()
    return {
        "status": "ok",
        "provider": current.provider,
        "available_providers": available_providers(),
        "model_client_ready": getattr(app.state, "model_client", None) is not None,
    }


app.include_router(chat_router)
