"""Chat API route."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.loop import run_agent
from app.agent.messages import AgentStep
from app.agent.model_client import ModelClientError, build_model_client
from app.core.config import get_settings
from app.tools.registry import build_tools

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    steps: list[AgentStep]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    tools = build_tools(settings.project_root)

    try:
        model_client = build_model_client(settings.provider, **settings.model_kwargs)
    except ModelClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        result = await run_agent(
            user_input=request.message,
            model_client=model_client,
            tools=tools,
            max_steps=settings.max_steps,
        )
    except ModelClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(answer=result.answer, steps=result.steps)
