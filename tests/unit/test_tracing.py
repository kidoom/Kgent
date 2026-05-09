"""Tests for D1 (Span + Tracer) and D2 (TraceExporter)"""

import json
import pytest

from kagent.core.tracing.models import Span, SpanType, SpanStatus
from kagent.core.tracing.tracer import Tracer
from kagent.core.tracing.exporter import TraceExporter


@pytest.fixture(autouse=True)
def reset_tracer():
    """Reset the Tracer singleton before each test."""
    Tracer.reset_instance()
    yield
    Tracer.reset_instance()


# ── D1: Span data model ────────────────────────────────────────────

class TestSpanCreation:
    def test_span_creation(self):
        """Span auto-generates span_id when not provided."""
        s = Span(name="test", type=SpanType.AGENT_RUN, trace_id="abc123")
        assert s.span_id is not None
        assert len(s.span_id) == 8
        assert s.name == "test"
        assert s.type == SpanType.AGENT_RUN
        assert s.trace_id == "abc123"
        assert s.parent_id is None
        assert s.status == SpanStatus.OK

    def test_span_with_explicit_id(self):
        s = Span(name="test", type=SpanType.LLM_CALL, trace_id="t1", span_id="custom")
        assert s.span_id == "custom"


# ── D1: Tracer ─────────────────────────────────────────────────────

class TestTracer:
    def test_tracer_singleton(self):
        """Tracer() returns the same instance."""
        t1 = Tracer()
        t2 = Tracer()
        assert t1 is t2

    def test_tracer_start_trace(self):
        """start_trace returns a root span with parent_id=None."""
        t = Tracer()
        root = t.start_trace("test_trace", input_text="hello")
        assert root.parent_id is None
        assert root.name == "test_trace"
        assert root.input == "hello"
        assert root.trace_id == root.span_id
        assert t.get_current_trace() is root

    def test_tracer_start_span(self):
        """start_span creates a child with parent_id pointing to root."""
        t = Tracer()
        root = t.start_trace("run")
        child = t.start_span("step1", SpanType.AGENT_STEP)
        assert child.parent_id == root.span_id
        assert child.trace_id == root.trace_id
        assert child in root.children

    def test_tracer_span_tree(self):
        """4-level nesting: trace → step → llm → tool."""
        t = Tracer()
        root = t.start_trace("run")
        step = t.start_span("step", SpanType.AGENT_STEP)
        llm = t.start_span("llm", SpanType.LLM_CALL)
        tool = t.start_span("tool", SpanType.TOOL_CALL)

        t.end_span(tool)
        t.end_span(llm)
        t.end_span(step)
        t.end_span(root)

        assert root.children[0] is step
        assert step.children[0] is llm
        assert llm.children[0] is tool
        assert tool.duration_ms is not None
        assert root.duration_ms is not None

    def test_tracer_context_manager(self):
        """Context manager auto-ends span with duration_ms."""
        t = Tracer()
        root = t.start_trace("run")
        with t.span("llm.call", SpanType.LLM_CALL) as s:
            pass
        assert s.duration_ms is not None
        assert s.status == SpanStatus.OK
        assert s.end_time is not None
        t.end_trace(root)

    def test_tracer_context_manager_error(self):
        """Context manager records ERROR status on exception."""
        t = Tracer()
        root = t.start_trace("run")
        with pytest.raises(ValueError):
            with t.span("llm.call", SpanType.LLM_CALL) as s:
                raise ValueError("boom")
        assert s.status == SpanStatus.ERROR
        assert "boom" in s.error
        t.end_trace(root)

    def test_tracer_without_trace(self):
        """start_span without start_trace raises RuntimeError."""
        t = Tracer()
        with pytest.raises(RuntimeError, match="No active trace"):
            t.start_span("step", SpanType.AGENT_STEP)

    def test_tracer_clear(self):
        """clear() removes all traces."""
        t = Tracer()
        t.start_trace("a")
        t.end_trace(t.get_current_trace())
        t.start_trace("b")
        t.end_trace(t.get_current_trace())
        assert len(t.get_all_traces()) == 2
        t.clear()
        assert len(t.get_all_traces()) == 0
        assert t.get_current_trace() is None

    def test_tracer_add_event(self):
        """add_event appends to the current span's events list."""
        t = Tracer()
        root = t.start_trace("run")
        t.add_event("llm.start", {"model": "gpt-4o"})
        assert len(root.events) == 1
        assert root.events[0]["name"] == "llm.start"
        t.end_trace(root)


# ── D2: TraceExporter ──────────────────────────────────────────────

class TestExporter:
    def _build_trace(self) -> Span:
        """Helper: build a small trace tree for exporter tests."""
        t = Tracer()
        root = t.start_trace("run", input_text="test input")
        root.metadata["run_id"] = "abc123"

        step = t.start_span("step1", SpanType.AGENT_STEP)
        llm = t.start_span("llm.call", SpanType.LLM_CALL)
        llm.metadata["token_usage"] = {"prompt": 100, "completion": 50, "total": 150}
        t.end_span(llm, output="response text")
        tool = t.start_span("tool.call.search", SpanType.TOOL_CALL)
        t.end_span(tool, output="search results")
        t.end_span(step)
        t.end_trace(root)
        return root

    def test_exporter_to_dict(self):
        """to_dict includes all fields and recursive children."""
        root = self._build_trace()
        d = TraceExporter.to_dict(root)

        assert d["name"] == "run"
        assert d["type"] == "agent.run"
        assert d["input"] == "test input"
        assert len(d["children"]) == 1  # one step

        step_d = d["children"][0]
        assert len(step_d["children"]) == 2  # llm + tool
        assert step_d["children"][0]["metadata"]["token_usage"]["prompt"] == 100

    def test_exporter_to_json(self):
        """to_json is valid JSON with summary fields."""
        root = self._build_trace()
        j = TraceExporter.to_json(root)
        d = json.loads(j)

        assert "total_tokens" in d
        assert d["total_tokens"]["prompt"] == 100
        assert d["total_tokens"]["completion"] == 50
        assert d["total_tokens"]["total"] == 150
        assert "total_duration_ms" in d
        assert "tool_call_count" in d
        assert d["tool_call_count"] == 1

    def test_exporter_to_tree(self):
        """to_tree output contains span names and durations."""
        root = self._build_trace()
        tree = TraceExporter.to_tree(root)

        assert "run" in tree
        assert "step1" in tree
        assert "llm.call" in tree
        assert "tool.call.search" in tree
        assert "ms" in tree
        assert "tokens:" in tree

    def test_exporter_error_span(self):
        """Error spans show ERROR status in tree."""
        t = Tracer()
        root = t.start_trace("run")
        with pytest.raises(RuntimeError):
            with t.span("failing_step", SpanType.LLM_CALL) as s:
                raise RuntimeError("api timeout")
        t.end_trace(root)

        tree = TraceExporter.to_tree(root)
        assert "ERROR" in tree
        assert "api timeout" in tree

    def test_exporter_to_json_error_span(self):
        """Error spans include error field in JSON."""
        t = Tracer()
        root = t.start_trace("run")
        with pytest.raises(RuntimeError):
            with t.span("fail", SpanType.TOOL_CALL):
                raise RuntimeError("tool broke")
        t.end_trace(root)

        d = json.loads(TraceExporter.to_json(root))
        child = d["children"][0]
        assert child["status"] == "error"
        assert "tool broke" in child["error"]

    def test_token_stats_in_json(self):
        """D8: to_json includes token_usage from events in the tree."""
        t = Tracer()
        root = t.start_trace("run", input_text="test")
        root.metadata["run_id"] = "abc123"

        llm = t.start_span("llm.call", SpanType.LLM_CALL)
        llm.metadata["token_usage"] = {"prompt": 200, "completion": 100, "total": 300}
        t.add_event("llm.end", {"token_usage": {"prompt": 200, "completion": 100, "total": 300}})
        t.end_span(llm)

        t.end_trace(root)

        d = json.loads(TraceExporter.to_json(root))
        assert d["total_tokens"]["prompt"] == 200
        assert d["total_tokens"]["completion"] == 100
        assert d["total_tokens"]["total"] == 300
        assert d["total_duration_ms"] is not None
        assert d["tool_call_count"] == 0

    def test_run_id_in_trace_metadata(self):
        """D8: run_id is stored in trace root metadata."""
        t = Tracer()
        root = t.start_trace("test.run", input_text="hi")
        root.metadata["run_id"] = "deadbeef"
        t.end_trace(root)

        d = json.loads(TraceExporter.to_json(root))
        assert d["metadata"]["run_id"] == "deadbeef"
