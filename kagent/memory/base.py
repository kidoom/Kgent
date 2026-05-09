"""Memory system: base classes and data models"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryItem(BaseModel):
    """A single memory entry."""

    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    score: float = 0.0


class BaseMemory(ABC):
    """Abstract base class for all memory backends.

    Implementations must provide store, search, and clear.
    """

    @abstractmethod
    def store(self, item: MemoryItem) -> None:
        """Store a memory item."""
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        """Search for relevant memories. Returns up to top_k items."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored memories."""
        ...
