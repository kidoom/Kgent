"""TraceExporter — dict / JSON / tree export for Span traces"""

import json
from typing import Optional

from .models import Span, SpanStatus


class TraceExporter:
    """Static utility to export a Span tree into dict, JSON, or terminal tree format."""

    @staticmethod
    def to_dict(span: Span) -> dict:
        """Recursively convert a Span tree to a plain dict."""
        d: dict = {
            "name": span.name,
            "type": span.type.value,
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_id": span.parent_id,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ms": span.duration_ms,
            "status": span.status.value,
        }
        if span.input:
            d["input"] = span.input
        if span.output:
            d["output"] = span.output
        if span.error:
            d["error"] = span.error
        if span.metadata:
            d["metadata"] = span.metadata
        if span.events:
            d["events"] = span.events
        if span.children:
            d["children"] = [TraceExporter.to_dict(c) for c in span.children]
        return d

    @staticmethod
    def to_json(span: Span, indent: int = 2) -> str:
        """Export to JSON string with top-level summary fields."""
        d = TraceExporter.to_dict(span)

        # Compute summary stats from the tree
        total_tokens = {"prompt": 0, "completion": 0, "total": 0}
        tool_call_count = 0
        TraceExporter._collect_stats(d, total_tokens, tool_call_count)
        tool_call_count = TraceExporter._count_type(d, "tool.call")

        d["total_tokens"] = total_tokens
        d["total_duration_ms"] = d.get("duration_ms")
        d["tool_call_count"] = tool_call_count

        return json.dumps(d, indent=indent, ensure_ascii=False)

    @staticmethod
    def _collect_stats(d: dict, tokens: dict, tool_count: int) -> None:
        """Walk the tree and accumulate token usage."""
        meta = d.get("metadata", {})
        usage = meta.get("token_usage")
        if usage:
            tokens["prompt"] += usage.get("prompt", 0)
            tokens["completion"] += usage.get("completion", 0)
            tokens["total"] += usage.get("total", 0)
        for child in d.get("children", []):
            TraceExporter._collect_stats(child, tokens, tool_count)

    @staticmethod
    def _count_type(d: dict, type_value: str) -> int:
        """Count spans of a given type in the tree."""
        count = 1 if d.get("type") == type_value else 0
        for child in d.get("children", []):
            count += TraceExporter._count_type(child, type_value)
        return count

    @staticmethod
    def to_tree(span: Span, indent: int = 0) -> str:
        """Export to a terminal-friendly tree string."""
        prefix = "  " * indent
        connector = "├── " if indent > 0 else ""
        duration_str = f" [{span.duration_ms}ms]" if span.duration_ms is not None else ""
        status_str = " ERROR" if span.status == SpanStatus.ERROR else ""
        tokens_str = ""
        usage = span.metadata.get("token_usage")
        if usage:
            tokens_str = f" tokens:{usage.get('prompt',0)}/{usage.get('completion',0)}"

        line = f"{prefix}{connector}{span.name}{duration_str}{tokens_str}{status_str}"
        lines = [line]

        if span.error:
            lines.append(f"{prefix}  └── error: {span.error}")

        for i, child in enumerate(span.children):
            lines.append(TraceExporter.to_tree(child, indent + 1))

        return "\n".join(lines)
