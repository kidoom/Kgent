"""WorkingMemory — short-term, capacity-limited, TTL-based memory."""

import time
from collections import OrderedDict

from .base import BaseMemory, MemoryItem


class WorkingMemory(BaseMemory):
    """In-memory short-term memory with TTL and capacity limits.

    - Items expire after `ttl` seconds (default 300 = 5 min).
    - Oldest items evicted when capacity is exceeded (LRU).
    - Search is simple substring matching (case-insensitive).
    """

    def __init__(self, capacity: int = 100, ttl: float = 300.0):
        self._capacity = capacity
        self._ttl = ttl
        # key → (timestamp, MemoryItem)
        self._store: OrderedDict[str, tuple[float, MemoryItem]] = OrderedDict()

    def store(self, item: MemoryItem) -> None:
        """Store an item with current timestamp. Evicts oldest if over capacity."""
        key = self._make_key(item)
        self._store[key] = (time.time(), item)
        self._store.move_to_end(key)
        self._evict_expired()
        while len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        """Search by substring match. Returns non-expired items sorted by score."""
        self._evict_expired()
        query_lower = query.lower()
        results = []
        for ts, item in self._store.values():
            if query_lower in item.content.lower():
                # Copy with computed score
                scored = item.model_copy()
                scored.score = 1.0  # Exact substring match
                results.append(scored)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear all stored items."""
        self._store.clear()

    def _evict_expired(self) -> None:
        """Remove items that have exceeded TTL."""
        now = time.time()
        expired_keys = [
            k for k, (ts, _) in self._store.items()
            if now - ts > self._ttl
        ]
        for k in expired_keys:
            del self._store[k]

    @staticmethod
    def _make_key(item: MemoryItem) -> str:
        """Generate a unique key from item content + timestamp."""
        return f"{item.content}:{item.created_at.isoformat()}"
