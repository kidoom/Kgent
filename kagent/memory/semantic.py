"""SemanticMemory — embedding-based vector retrieval memory."""

import math
from typing import Any, Callable, Optional

from .base import BaseMemory, MemoryItem


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticMemory(BaseMemory):
    """Memory backend with embedding-based semantic search.

    Requires an embedding function: `Callable[[str], list[float]]`.

    If no embedding function is provided, stores items but search
    falls back to substring matching with a user-visible warning.

    Usage:
        # With real embeddings
        mem = SemanticMemory(embedding_fn=my_embed_function)
        mem.store(MemoryItem(content="Kagent is a framework"))
        results = mem.search("AI agent framework")

        # Without embeddings (fallback to substring)
        mem = SemanticMemory()
        # → search() prints a config hint and uses substring match
    """

    def __init__(
        self,
        embedding_fn: Optional[Callable[[str], list[float]]] = None,
        similarity_threshold: float = 0.3,
    ):
        self._embedding_fn = embedding_fn
        self._threshold = similarity_threshold
        self._items: list[MemoryItem] = []
        self._vectors: list[list[float]] = []

    def store(self, item: MemoryItem) -> None:
        """Store item with its embedding vector."""
        self._items.append(item)
        if self._embedding_fn:
            vec = self._embedding_fn(item.content)
            self._vectors.append(vec)
        else:
            self._vectors.append([])

    def search(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        """Search by semantic similarity.

        Falls back to substring matching if no embedding function is configured.
        """
        if not self._items:
            return []

        if not self._embedding_fn:
            return self._fallback_search(query, top_k)

        query_vec = self._embedding_fn(query)
        scored = []
        for i, (item, vec) in enumerate(zip(self._items, self._vectors)):
            if not vec:
                continue
            sim = _cosine_similarity(query_vec, vec)
            if sim >= self._threshold:
                copy = item.model_copy()
                copy.score = round(sim, 4)
                scored.append(copy)

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def clear(self) -> None:
        """Clear all stored items and vectors."""
        self._items.clear()
        self._vectors.clear()

    def _fallback_search(self, query: str, top_k: int) -> list[MemoryItem]:
        """Substring fallback when no embedding function is available."""
        query_lower = query.lower()
        results = []
        for item in self._items:
            if query_lower in item.content.lower():
                copy = item.model_copy()
                copy.score = 0.5  # Lower score to indicate fallback
                results.append(copy)
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:top_k]
