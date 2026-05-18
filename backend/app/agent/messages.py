"""Message and agent-loop data models."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolUseBlock(BaseModel):
    """A model request to call a runtime tool."""

    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResultBlock(BaseModel):
    """A runtime observation returned to the model as user content."""

    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


class Message(BaseModel):
    """The minimal message shape used by Kgent V0.1."""

    role: Literal["system", "user", "assistant"]
    content: str | list[ToolUseBlock] | list[ToolResultBlock]


class ModelResponse(BaseModel):
    """Normalized model output consumed by the loop controller."""

    assistant_message: Message
    text: str = ""
    tool_uses: list[ToolUseBlock] = Field(default_factory=list)


class ToolExecutionResult(BaseModel):
    """Result of executing one tool_use block."""

    content: str
    is_error: bool = False


class AgentStep(BaseModel):
    """Frontend-friendly trace of what the agent did."""

    type: Literal["tool_use", "tool_result"]
    name: str
    input: dict[str, Any] | None = None
    content: str | None = None
    is_error: bool = False


class AgentResult(BaseModel):
    """Final response returned by the API."""

    answer: str
    steps: list[AgentStep] = Field(default_factory=list)
