"""Chat API route."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.runtime.loop import run_agent
from app.runtime.messages import AgentStep
from app.model_client import ModelClientError, ModelClientProtocol, build_model_client
from app.runtime.permissions import AllowAllPolicy, RiskBasedPolicy, PermissionPolicy
from app.core.config import get_settings
from app.tools.registry import build_tools

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str = Field(default="default", min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    steps: list[AgentStep]
    message_count: int


def _resolve_model_client(
    request: Request,
    provider: str,
    model_kwargs: dict[str, object],
) -> tuple[ModelClientProtocol, bool]:
    shared = getattr(request.app.state, "model_client", None)
    if shared is not None and provider == "openai":
        return shared, False
    return build_model_client(provider, **model_kwargs), True


def build_api_policy(permission_mode: str) -> PermissionPolicy:
    """Construct the policy used for HTTP requests.

    Interactive mode is forcibly downgraded to `risk_based` here because the
    API has no way to prompt the user without blocking the HTTP request.
    """
    if permission_mode == "allow_all":
        return AllowAllPolicy()
    return RiskBasedPolicy()


def resolve_api_permission_mode(permission_mode: str) -> str:
    """Effective mode applied on the API side (interactive -> risk_based)."""
    if permission_mode == "allow_all":
        return "allow_all"
    return "risk_based"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    settings = get_settings()
    tools = build_tools(settings.project_root)

    try:
        model_client, owns_client = _resolve_model_client(request, settings.provider, settings.model_kwargs)
    except ModelClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    policy = build_api_policy(settings.permission_mode)

    try:
        result = await run_agent(
            user_input=body.message,
            model_client=model_client,
            tools=tools,
            max_steps=settings.max_steps,
            session_id=body.session_id,
            max_session_messages=settings.max_session_messages,
            policy=policy,
        )
    except ModelClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if owns_client and hasattr(model_client, "close"):
            await model_client.close()

    return ChatResponse(
        session_id=result.session_id,
        answer=result.answer,
        steps=result.steps,
        message_count=result.message_count,
    )
