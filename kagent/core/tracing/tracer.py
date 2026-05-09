"""Tracer singleton — contextvars-based concurrent trace isolation"""

import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from .models import Span, SpanType, SpanStatus

# ContextVar for concurrent isolation — each async task / thread gets its own trace
_current_trace: ContextVar[Optional[Span]] = ContextVar("_current_trace", default=None)
_current_span_stack: ContextVar[list[Span]] = ContextVar("_current_span_stack", default=[])


class Tracer:
    """Singleton trace collector with contextvars-based concurrency isolation.

    Usage:
        tracer = Tracer()
        root = tracer.start_trace("agent.run", input_text="hello")
        with tracer.span("llm.call", SpanType.LLM_CALL) as s:
            ...
        tracer.end_trace(root)
    """

    _instance: Optional["Tracer"] = None

    def __new__(cls) -> "Tracer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._traces: list[Span] = []
        return cls._instance

    def start_trace(self, name: str, input_text: str = "") -> Span:
        """Start a new root trace span."""
        trace_id = uuid.uuid4().hex[:8]
        root = Span(
            name=name,
            type=SpanType.AGENT_RUN,
            trace_id=trace_id,
            span_id=trace_id,
            start_time=time.time(),
            input=input_text[:500] if input_text else None,
        )
        _current_trace.set(root)
        _current_span_stack.set([root])
        self._traces.append(root)
        return root

    def start_span(
        self,
        name: str,
        type: SpanType,
        input_data: str = "",
        **metadata,
    ) -> Span:
        """Start a child span under the current active span."""
        trace = _current_trace.get()
        if trace is None:
            raise RuntimeError("No active trace. Call start_trace() first.")

        stack = _current_span_stack.get()
        parent = stack[-1] if stack else trace

        span = Span(
            name=name,
            type=type,
            trace_id=trace.trace_id,
            parent_id=parent.span_id,
            start_time=time.time(),
            input=input_data[:500] if input_data else None,
            metadata=metadata if metadata else {},
        )
        parent.children.append(span)
        stack.append(span)
        _current_span_stack.set(stack)
        return span

    def end_span(
        self,
        span: Span,
        output: str = "",
        status: SpanStatus = SpanStatus.OK,
        error: str = "",
    ) -> Span:
        """End a span — records duration and pops from stack."""
        span.end_time = time.time()
        span.duration_ms = round((span.end_time - span.start_time) * 1000, 2)
        if output:
            span.output = output[:500]
        span.status = status
        if error:
            span.error = error[:500]

        stack = _current_span_stack.get()
        if stack and stack[-1].span_id == span.span_id:
            stack.pop()
            _current_span_stack.set(stack)
        return span

    @contextmanager
    def span(self, name: str, type: SpanType, **metadata):
        """Context manager — auto start/end span with exception handling."""
        s = self.start_span(name, type, **metadata)
        try:
            yield s
        except Exception as e:
            self.end_span(s, status=SpanStatus.ERROR, error=str(e))
            raise
        else:
            self.end_span(s)

    def end_trace(self, root: Span) -> None:
        """End the root trace span."""
        if root.end_time is None:
            self.end_span(root)
        _current_trace.set(None)
        _current_span_stack.set([])

    def add_event(self, name: str, data: dict) -> None:
        """Add an event to the current active span."""
        stack = _current_span_stack.get()
        if not stack:
            return
        current = stack[-1]
        current.events.append({"name": name, "data": data, "time": time.time()})

    def get_current_trace(self) -> Optional[Span]:
        """Return the current active root trace, or None."""
        return _current_trace.get()

    def get_all_traces(self) -> list[Span]:
        """Return all completed and in-progress traces."""
        return list(self._traces)

    def clear(self) -> None:
        """Clear all traces and reset state."""
        self._traces.clear()
        _current_trace.set(None)
        _current_span_stack.set([])

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (mainly for testing)."""
        cls._instance = None
