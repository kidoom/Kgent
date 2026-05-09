"""Tests for E1 (Memory base + Manager), E2 (Working + Episodic),
E2.5 (Semantic), and E3 (MemoryTool)."""

import time
from datetime import datetime, timezone, timedelta

import pytest

from kagent.memory.base import BaseMemory, MemoryItem
from kagent.memory.manager import MemoryManager
from kagent.memory.working import WorkingMemory
from kagent.memory.episodic import EpisodicMemory
from kagent.memory.semantic import SemanticMemory
from kagent.memory.tool import MemoryTool
from kagent.tools.base import ToolResult


# ── E1: BaseMemory + MemoryManager ─────────────────────────────────

class TestBaseMemory:
    def test_base_memory_is_abstract(self):
        """BaseMemory cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseMemory()

    def test_memory_item_create(self):
        """MemoryItem creates with defaults."""
        item = MemoryItem(content="hello")
        assert item.content == "hello"
        assert item.metadata == {}
        assert item.score == 0.0
        assert item.created_at is not None

    def test_memory_item_with_metadata(self):
        """MemoryItem accepts custom metadata."""
        item = MemoryItem(content="test", metadata={"source": "user"}, score=0.9)
        assert item.metadata["source"] == "user"
        assert item.score == 0.9


class TestMemoryManager:
    def test_register_and_list(self):
        """Register backends and list them."""
        mgr = MemoryManager()
        mgr.register("working", WorkingMemory())
        mgr.register("episodic", EpisodicMemory())
        assert set(mgr.list_backends()) == {"working", "episodic"}

    def test_register_non_memory_raises(self):
        """Registering a non-BaseMemory raises TypeError."""
        mgr = MemoryManager()
        with pytest.raises(TypeError):
            mgr.register("bad", "not a memory")

    def test_unregister(self):
        """Unregister removes backend."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        assert mgr.unregister("w") is True
        assert mgr.unregister("w") is False
        assert mgr.list_backends() == []

    def test_store_all_backends(self):
        """store() without backend name stores in all."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        mgr.register("e", EpisodicMemory())
        item = MemoryItem(content="hello")
        mgr.store(item)
        assert len(mgr.search("hello", backend="w")) == 1
        assert len(mgr.search("hello", backend="e")) == 1

    def test_store_specific_backend(self):
        """store() with backend name stores only there."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        mgr.register("e", EpisodicMemory())
        mgr.store(MemoryItem(content="hello"), backend="w")
        assert len(mgr.search("hello", backend="w")) == 1
        assert len(mgr.search("hello", backend="e")) == 0

    def test_search_merged_results(self):
        """search() across all backends merges by score."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        mgr.register("e", EpisodicMemory())
        mgr.store(MemoryItem(content="alpha"))
        mgr.store(MemoryItem(content="alpha again"))
        results = mgr.search("alpha", top_k=10)
        assert len(results) >= 2

    def test_clear_all(self):
        """clear() without name clears all backends."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        mgr.register("e", EpisodicMemory())
        mgr.store(MemoryItem(content="test"))
        mgr.clear()
        assert len(mgr.search("test", backend="w")) == 0
        assert len(mgr.search("test", backend="e")) == 0


# ── E2: WorkingMemory ──────────────────────────────────────────────

class TestWorkingMemory:
    def test_store_and_search(self):
        """Basic store and substring search."""
        wm = WorkingMemory()
        wm.store(MemoryItem(content="用户叫张三"))
        results = wm.search("张三")
        assert len(results) == 1
        assert "张三" in results[0].content

    def test_search_no_match(self):
        """Search with no match returns empty."""
        wm = WorkingMemory()
        wm.store(MemoryItem(content="hello"))
        assert wm.search("world") == []

    def test_capacity_eviction(self):
        """Exceeding capacity evicts oldest items."""
        wm = WorkingMemory(capacity=3)
        for i in range(5):
            wm.store(MemoryItem(content=f"item {i}"))
        # Only last 3 should remain
        results = wm.search("item", top_k=10)
        assert len(results) == 3
        contents = {r.content for r in results}
        assert "item 4" in contents
        assert "item 2" in contents
        assert "item 0" not in contents

    def test_ttl_expiry(self):
        """Items expire after TTL."""
        wm = WorkingMemory(ttl=0.1)
        wm.store(MemoryItem(content="ephemeral"))
        time.sleep(0.15)
        assert wm.search("ephemeral") == []

    def test_search_case_insensitive(self):
        """Search is case-insensitive."""
        wm = WorkingMemory()
        wm.store(MemoryItem(content="Python"))
        assert len(wm.search("python")) == 1

    def test_clear(self):
        """clear() removes all items."""
        wm = WorkingMemory()
        wm.store(MemoryItem(content="test"))
        wm.clear()
        assert wm.search("test") == []


# ── E2: EpisodicMemory ─────────────────────────────────────────────

class TestEpisodicMemory:
    def test_store_and_search(self):
        """Basic store and search."""
        em = EpisodicMemory()
        em.store(MemoryItem(content="今天天气很好"))
        results = em.search("天气")
        assert len(results) == 1

    def test_chronological_order(self):
        """Results sorted by created_at descending (newest first)."""
        em = EpisodicMemory()
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
        em.store(MemoryItem(content="event A", created_at=t1))
        em.store(MemoryItem(content="event B", created_at=t2))
        results = em.search("event", top_k=10)
        assert results[0].content == "event B"

    def test_time_range_filter(self):
        """after/before filters work."""
        em = EpisodicMemory()
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
        t3 = datetime(2026, 12, 1, tzinfo=timezone.utc)
        em.store(MemoryItem(content="winter", created_at=t1))
        em.store(MemoryItem(content="summer", created_at=t2))
        em.store(MemoryItem(content="winter again", created_at=t3))

        # After July
        results = em.search("", top_k=10, after=datetime(2026, 7, 1, tzinfo=timezone.utc))
        assert len(results) == 1
        assert results[0].content == "winter again"

    def test_count_and_get_all(self):
        """count() and get_all() work."""
        em = EpisodicMemory()
        em.store(MemoryItem(content="a"))
        em.store(MemoryItem(content="b"))
        assert em.count() == 2
        assert len(em.get_all()) == 2

    def test_clear(self):
        """clear() removes all episodes."""
        em = EpisodicMemory()
        em.store(MemoryItem(content="test"))
        em.clear()
        assert em.count() == 0


# ── E2.5: SemanticMemory ───────────────────────────────────────────

class TestSemanticMemory:
    def test_with_embedding_fn(self):
        """Semantic search with mock embedding function."""
        # Simple hash-based mock embedding
        def mock_embed(text: str) -> list[float]:
            # Create a simple 3D vector from character sums
            s = sum(ord(c) for c in text)
            return [float(s % 10) / 10, float(s % 7) / 7, float(s % 3) / 3]

        sm = SemanticMemory(embedding_fn=mock_embed)
        sm.store(MemoryItem(content="Python is great"))
        sm.store(MemoryItem(content="JavaScript is popular"))
        sm.store(MemoryItem(content="Python for data science"))

        # Should find Python-related items
        results = sm.search("Python programming", top_k=3)
        assert len(results) > 0
        assert results[0].score > 0

    def test_without_embedding_fn_fallback(self):
        """Without embedding function, falls back to substring match."""
        sm = SemanticMemory()
        sm.store(MemoryItem(content="hello world"))
        sm.store(MemoryItem(content="goodbye world"))

        results = sm.search("hello")
        assert len(results) == 1
        assert results[0].score == 0.5  # Fallback score

    def test_similarity_threshold(self):
        """Items below threshold are excluded."""
        def mock_embed(text: str) -> list[float]:
            return [1.0, 0.0, 0.0] if "A" in text else [0.0, 1.0, 0.0]

        sm = SemanticMemory(embedding_fn=mock_embed, similarity_threshold=0.9)
        sm.store(MemoryItem(content="A topic"))
        sm.store(MemoryItem(content="B topic"))

        results = sm.search("A query")
        # Only A should match (high similarity with A query)
        assert len(results) == 1
        assert "A" in results[0].content

    def test_clear(self):
        """clear() removes all items and vectors."""
        sm = SemanticMemory()
        sm.store(MemoryItem(content="test"))
        sm.clear()
        assert sm.search("test") == []


# ── E3: MemoryTool ─────────────────────────────────────────────────

class TestMemoryTool:
    def test_remember_and_recall(self):
        """Remember then recall works."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        tool = MemoryTool(mgr)

        # Remember
        r = tool.run({"action": "remember", "content": "用户叫张三"})
        assert r.success is True
        assert "已记住" in r.content

        # Recall
        r = tool.run({"action": "recall", "query": "张三"})
        assert r.success is True
        assert "张三" in r.content

    def test_recall_no_results(self):
        """Recall with no match returns friendly message."""
        mgr = MemoryManager()
        mgr.register("w", WorkingMemory())
        tool = MemoryTool(mgr)

        r = tool.run({"action": "recall", "query": "nothing"})
        assert r.success is True
        assert "未找到" in r.content

    def test_remember_missing_content(self):
        """Remember without content returns error."""
        mgr = MemoryManager()
        tool = MemoryTool(mgr)
        r = tool.run({"action": "remember"})
        assert r.success is False

    def test_recall_missing_query(self):
        """Recall without query returns error."""
        mgr = MemoryManager()
        tool = MemoryTool(mgr)
        r = tool.run({"action": "recall"})
        assert r.success is False

    def test_invalid_action(self):
        """Unknown action returns error."""
        mgr = MemoryManager()
        tool = MemoryTool(mgr)
        r = tool.run({"action": "delete"})
        assert r.success is False
        assert "未知" in r.content

    def test_get_parameters(self):
        """Tool has correct parameters."""
        mgr = MemoryManager()
        tool = MemoryTool(mgr)
        params = tool.get_parameters()
        names = {p.name for p in params}
        assert "action" in names
        assert "content" in names
        assert "query" in names
