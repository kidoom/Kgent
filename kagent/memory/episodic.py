"""EpisodicMemory — time-series memory with temporal retrieval."""

from datetime import datetime, timezone
from typing import Optional

from .base import BaseMemory, MemoryItem


class EpisodicMemory(BaseMemory):
    """Append-only time-series memory with time-range retrieval.

    - Items stored in insertion order (by created_at).
    - Search supports time-range filtering and substring matching.
    - No capacity limit (designed for persistent episode logging).
    """

    def __init__(self):
        self._items: list[MemoryItem] = []

    def store(self, item: MemoryItem) -> None:
        """Append an item to the episode log."""
        self._items.append(item)

    def search(
        self,
        query: str,
        top_k: int = 5,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
    ) -> list[MemoryItem]:
        """Search episodes by substring and optional time range.

        Args:
            query: Substring to match (case-insensitive).
            top_k: Max results.
            after: Only include items created after this time.
            before: Only include items created before this time.

        Returns:
            Matching items sorted by created_at descending.
        """
        query_lower = query.lower()
        results = []
        for item in self._items:
            # Time range filter
            if after and item.created_at < after:
                continue
            if before and item.created_at > before:
                continue
            # Substring match
            if query_lower in item.content.lower():
                scored = item.model_copy()
                scored.score = 1.0
                results.append(scored)

        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear all episodes."""
        self._items.clear()

    def get_all(self) -> list[MemoryItem]:
        """Return all items in chronological order."""
        return list(self._items)

    def count(self) -> int:
        """Return the number of stored episodes."""
        return len(self._items)
