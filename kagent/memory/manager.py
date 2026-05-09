"""MemoryManager — multi-backend memory orchestrator."""

from typing import Optional

from .base import BaseMemory, MemoryItem


class MemoryManager:
    """Manages multiple memory backends with unified store/search.

    Usage:
        manager = MemoryManager()
        manager.register("working", WorkingMemory())
        manager.register("episodic", EpisodicMemory())

        manager.store(MemoryItem(content="hello"))
        results = manager.search("hello", top_k=5)
    """

    def __init__(self):
        self._backends: dict[str, BaseMemory] = {}

    def register(self, name: str, backend: BaseMemory) -> None:
        """Register a memory backend."""
        if not isinstance(backend, BaseMemory):
            raise TypeError(f"Expected BaseMemory instance, got {type(backend).__name__}")
        self._backends[name] = backend

    def unregister(self, name: str) -> bool:
        """Unregister a memory backend. Returns True if removed."""
        if name in self._backends:
            del self._backends[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseMemory]:
        """Get a specific backend by name."""
        return self._backends.get(name)

    def store(self, item: MemoryItem, backend: Optional[str] = None) -> None:
        """Store an item in one or all backends.

        Args:
            item: The memory item to store.
            backend: If specified, store only in this backend. Otherwise store in all.
        """
        if backend:
            if backend not in self._backends:
                raise KeyError(f"Memory backend '{backend}' not registered")
            self._backends[backend].store(item)
        else:
            for b in self._backends.values():
                b.store(item)

    def search(self, query: str, top_k: int = 5, backend: Optional[str] = None) -> list[MemoryItem]:
        """Search across one or all backends and merge results by score.

        Args:
            query: Search query string.
            top_k: Maximum results to return.
            backend: If specified, search only this backend. Otherwise search all.

        Returns:
            Merged and sorted list of MemoryItems, up to top_k.
        """
        if backend:
            if backend not in self._backends:
                raise KeyError(f"Memory backend '{backend}' not registered")
            return self._backends[backend].search(query, top_k)

        all_items: list[MemoryItem] = []
        for b in self._backends.values():
            all_items.extend(b.search(query, top_k))

        # Sort by score descending, then by created_at descending
        all_items.sort(key=lambda x: (x.score, x.created_at), reverse=True)
        return all_items[:top_k]

    def clear(self, backend: Optional[str] = None) -> None:
        """Clear one or all backends."""
        if backend:
            if backend not in self._backends:
                raise KeyError(f"Memory backend '{backend}' not registered")
            self._backends[backend].clear()
        else:
            for b in self._backends.values():
                b.clear()

    def list_backends(self) -> list[str]:
        """Return names of all registered backends."""
        return list(self._backends.keys())
