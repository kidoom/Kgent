"""Tests for E4: ContextBuilder (GSSC pipeline)."""

import pytest

from kagent.context.builder import ContextBuilder


class TestContextBuilder:
    def test_gather_messages(self):
        """Gather collects messages."""
        cb = ContextBuilder()
        items = cb.gather(messages=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ])
        assert len(items) == 2
        assert items[0]["type"] == "message"
        assert "hello" in items[0]["content"]

    def test_gather_tool_results(self):
        """Gather collects tool results."""
        cb = ContextBuilder()
        items = cb.gather(tool_results=["result1", "result2"])
        assert len(items) == 2
        assert items[0]["type"] == "tool_result"

    def test_gather_memories(self):
        """Gather collects memories with lower score."""
        cb = ContextBuilder()
        items = cb.gather(memories=["mem1", "mem2"])
        assert len(items) == 2
        assert items[0]["score"] == 0.7

    def test_gather_all_sources(self):
        """Gather combines all sources."""
        cb = ContextBuilder()
        items = cb.gather(
            messages=[{"role": "user", "content": "q"}],
            tool_results=["tr"],
            memories=["m"],
            extra="extra",
        )
        assert len(items) == 4
        types = {i["type"] for i in items}
        assert types == {"message", "tool_result", "memory", "extra"}

    def test_select_filters_by_score(self):
        """Select removes items below min_score."""
        cb = ContextBuilder()
        items = [
            {"type": "message", "content": "a", "score": 1.0},
            {"type": "memory", "content": "b", "score": 0.3},
            {"type": "extra", "content": "c", "score": 0.1},
        ]
        filtered = cb.select(items, min_score=0.5)
        assert len(filtered) == 1
        assert filtered[0]["content"] == "a"

    def test_structure_groups_by_type(self):
        """Structure formats items into sections."""
        cb = ContextBuilder()
        items = [
            {"type": "message", "content": "user: hi", "score": 1.0},
            {"type": "tool_result", "content": "search result", "score": 0.9},
            {"type": "memory", "content": "remember this", "score": 0.7},
        ]
        text = cb.structure(items)
        assert "## 对话历史" in text
        assert "user: hi" in text
        assert "## 工具结果" in text
        assert "## 相关记忆" in text

    def test_compress_short_text_unchanged(self):
        """Short text passes through compress unchanged."""
        cb = ContextBuilder(max_tokens=1000)
        text = "short text"
        assert cb.compress(text) == text

    def test_compress_long_text_truncated(self):
        """Long text gets truncated from the beginning."""
        cb = ContextBuilder(max_tokens=10, chars_per_token=1.0)  # 10 chars max
        text = "a" * 5 + "\n" + "b" * 20
        result = cb.compress(text)
        assert len(result) <= 50  # Some overhead for prefix
        assert "b" * 5 in result  # Tail preserved

    def test_build_full_pipeline(self):
        """build() runs the full GSSC pipeline."""
        cb = ContextBuilder(max_tokens=1000)
        result = cb.build(
            messages=[{"role": "user", "content": "what is Python?"}],
            tool_results=["Python is a programming language"],
            memories=["User likes Python"],
        )
        assert "Python" in result
        assert "## 对话历史" in result

    def test_build_with_min_score(self):
        """build() respects min_score parameter."""
        cb = ContextBuilder(max_tokens=1000)
        result = cb.build(
            messages=[{"role": "user", "content": "test"}],
            memories=["low score item"],
            min_score=0.8,  # memories have score 0.7, should be filtered
        )
        # Memory section should not appear (score 0.7 < 0.8)
        assert "## 相关记忆" not in result
