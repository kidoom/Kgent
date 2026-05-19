"""Message and agent-loop data models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
    # Visible plan/reasoning text when the assistant reply also includes tool_use blocks.
    assistant_text: str | None = None


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
    """Observable agent-loop trace for API, frontend, and debug CLI (V0.1.2)."""

    type: Literal["think", "call", "observe", "final"]
    turn_index: int
    content: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    is_error: bool = False

    @model_validator(mode="after")
    def validate_fields_for_type(self) -> "AgentStep":
        if self.type == "think":
            if not self.content or not self.content.strip():
                raise ValueError("think step requires non-empty content")
        elif self.type == "final":
            if self.content is None:
                raise ValueError("final step requires content")
        elif self.type == "call":
            if not self.tool_use_id or not self.tool_name:
                raise ValueError("call step requires tool_use_id and tool_name")
            if self.tool_input is None:
                raise ValueError("call step requires tool_input")
        elif self.type == "observe":
            if not self.tool_use_id or not self.tool_name:
                raise ValueError("observe step requires tool_use_id and tool_name")
            if self.content is None:
                raise ValueError("observe step requires content")
        return self


class AgentResult(BaseModel):
    """Final response returned by the API."""

    answer: str
    steps: list[AgentStep] = Field(default_factory=list)
    session_id: str = "default"
    message_count: int = 0
