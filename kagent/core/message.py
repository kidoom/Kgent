"""Message system for Agent conversations"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in an Agent conversation"""

    content: str
    role: Literal["user", "assistant", "system", "tool"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert to OpenAI-compatible message format"""
        return {"role": self.role, "content": self.content}
