"""ContextBuilder — GSSC (Gather → Select → Structure → Compress) pipeline."""

from typing import Any, Optional


class ContextBuilder:
    """Builds optimized context for LLM calls using the GSSC pipeline.

    GSSC stages:
      1. Gather   — collect raw inputs (messages, tool results, memories)
      2. Select   — filter by relevance score
      3. Structure — format into a prompt-ready template
      4. Compress — truncate to fit within max_tokens

    Usage:
        builder = ContextBuilder(max_tokens=4000)
        context = builder.build(
            messages=[...],
            tool_results=[...],
            memories=[...],
        )
    """

    def __init__(self, max_tokens: int = 4000, chars_per_token: float = 3.5):
        self._max_tokens = max_tokens
        self._chars_per_token = chars_per_token

    def gather(
        self,
        messages: Optional[list[dict]] = None,
        tool_results: Optional[list[str]] = None,
        memories: Optional[list[str]] = None,
        extra: Optional[str] = None,
    ) -> list[dict]:
        """Stage 1: Gather all inputs into a unified list.

        Returns list of {"type": str, "content": str, "score": float}.
        """
        items = []
        for msg in (messages or []):
            items.append({
                "type": "message",
                "content": f"{msg.get('role', 'unknown')}: {msg.get('content', '')}",
                "score": 1.0,
            })
        for tr in (tool_results or []):
            items.append({"type": "tool_result", "content": tr, "score": 0.9})
        for mem in (memories or []):
            items.append({"type": "memory", "content": mem, "score": 0.7})
        if extra:
            items.append({"type": "extra", "content": extra, "score": 0.5})
        return items

    def select(self, items: list[dict], min_score: float = 0.0) -> list[dict]:
        """Stage 2: Filter items by minimum relevance score."""
        return [i for i in items if i.get("score", 0.0) >= min_score]

    def structure(self, items: list[dict]) -> str:
        """Stage 3: Format items into a prompt-ready context string."""
        sections = {
            "message": [],
            "tool_result": [],
            "memory": [],
            "extra": [],
        }
        for item in items:
            sections.get(item["type"], sections["extra"]).append(item["content"])

        parts = []
        if sections["message"]:
            parts.append("## 对话历史\n" + "\n".join(sections["message"]))
        if sections["tool_result"]:
            parts.append("## 工具结果\n" + "\n".join(sections["tool_result"]))
        if sections["memory"]:
            parts.append("## 相关记忆\n" + "\n".join(sections["memory"]))
        if sections["extra"]:
            parts.append("\n".join(sections["extra"]))

        return "\n\n".join(parts)

    def compress(self, text: str) -> str:
        """Stage 4: Truncate text to fit within max_tokens.

        Uses a simple char-based approximation (chars_per_token).
        Preserves the end of the text (most recent context is most relevant).
        """
        max_chars = int(self._max_tokens * self._chars_per_token)
        if len(text) <= max_chars:
            return text
        # Keep the tail (most recent), truncate the beginning
        truncated = text[-max_chars:]
        # Find a clean line break
        newline_idx = truncated.find("\n")
        if newline_idx > 0 and newline_idx < 200:
            truncated = truncated[newline_idx + 1:]
        return f"[... 已压缩 ...]\n{truncated}"

    def build(
        self,
        messages: Optional[list[dict]] = None,
        tool_results: Optional[list[str]] = None,
        memories: Optional[list[str]] = None,
        extra: Optional[str] = None,
        min_score: float = 0.0,
    ) -> str:
        """Run the full GSSC pipeline and return a context string."""
        items = self.gather(messages, tool_results, memories, extra)
        items = self.select(items, min_score)
        context = self.structure(items)
        return self.compress(context)
