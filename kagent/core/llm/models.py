"""LLM data models: response and streaming chunk"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Response from LLM provider"""

    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    usage: Optional[dict] = None
    raw: Any = None


class LLMChunk(BaseModel):
    """Streaming chunk from LLM provider"""

    delta: str
    usage: Optional[dict] = None
    raw: Any = None
