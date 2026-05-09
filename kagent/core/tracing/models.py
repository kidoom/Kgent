"""Tracing data models: Span, SpanType, SpanStatus"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpanType(str, Enum):
    """Types of trace spans"""
    AGENT_RUN = "agent.run"
    AGENT_STEP = "agent.step"
    LLM_CALL = "llm.call"
    TOOL_CALL = "tool.call"


class SpanStatus(str, Enum):
    """Span execution status"""
    OK = "ok"
    ERROR = "error"


@dataclass
class Span:
    """A single trace span — forms a tree via parent_id / children."""

    name: str
    type: SpanType
    trace_id: str
    span_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])
    parent_id: str | None = None
    start_time: float = 0.0
    end_time: float | None = None
    duration_ms: float | None = None
    input: str | None = None
    output: str | None = None
    status: SpanStatus = SpanStatus.OK
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    children: list["Span"] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
