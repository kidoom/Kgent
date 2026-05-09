"""D3 integration tests: Agent tracing produces correct Span trees."""

import pytest
from unittest.mock import MagicMock

from kagent.core.config import Config
from kagent.core.llm import AgentLLM, LLMResponse
from kagent.core.tracing import Tracer, SpanType, TraceExporter
from kagent.core.tracing.models import SpanStatus
from kagent.agents.simple_agent import SimpleAgent
from kagent.agents.react_agent import ReActAgent
from kagent.tools.registry import ToolRegistry


@pytest.fixture(autouse=True)
def reset_tracer():
    """Reset Tracer singleton before each test."""
    Tracer.reset_instance()
    yield
    Tracer.reset_instance()


def _mock_llm(responses: list[str]) -> AgentLLM:
    """Create a mock AgentLLM that returns responses in sequence."""
    llm = MagicMock(spec=AgentLLM)
    llm.invoke.side_effect = [
        LLMResponse(content=r, usage={"prompt": 100, "completion": 50, "total": 150})
        for r in responses
    ]
    return llm


class TestSimpleAgentTracing:
    def test_simple_agent_has_full_trace(self):
        """SimpleAgent.run() produces a trace with AGENT_RUN root."""
        llm = _mock_llm(["Hello!"])
        agent = SimpleAgent(name="test", llm=llm, config=Config(api_key="x"))
        result = agent.run("hi")

        traces = Tracer().get_all_traces()
        assert len(traces) == 1
        assert traces[0].type == SpanType.AGENT_RUN
        assert traces[0].name == "test.run"
        assert traces[0].metadata.get("run_id") is not None

    def test_simple_agent_trace_contains_llm_call(self):
        """SimpleAgent trace has LLM_CALL child span."""
        llm = _mock_llm(["answer"])
        agent = SimpleAgent(name="test", llm=llm, config=Config(api_key="x"))
        agent.run("hi")

        root = Tracer().get_all_traces()[0]
        llm_spans = [c for c in root.children if c.type == SpanType.LLM_CALL]
        assert len(llm_spans) == 1
        assert llm_spans[0].metadata.get("token_usage") == {
            "prompt": 100, "completion": 50, "total": 150,
        }

    def test_simple_agent_with_tools_trace(self):
        """SimpleAgent with tools produces LLM + TOOL_CALL spans."""
        llm = _mock_llm([
            "[TOOL_CALL:echo:hello]",
            "Tool said: hello",
        ])
        agent = SimpleAgent(
            name="test", llm=llm, config=Config(api_key="x"),
            tool_registry=ToolRegistry(),
        )
        agent.tool_registry.register_function(
            "echo", "echo tool", lambda args: args.get("query", "")
        )
        agent.run("hi")

        root = Tracer().get_all_traces()[0]
        # Find TOOL_CALL spans in the tree
        all_spans = _flatten(root)
        tool_spans = [s for s in all_spans if s.type == SpanType.TOOL_CALL]
        assert len(tool_spans) >= 1
        assert tool_spans[0].name == "tool.call.echo"

    def test_simple_agent_tracing_disabled(self):
        """When enable_tracing=False, no traces are produced."""
        llm = _mock_llm(["answer"])
        agent = SimpleAgent(
            name="test", llm=llm, config=Config(api_key="x"),
            enable_tracing=False,
        )
        agent.run("hi")
        assert len(Tracer().get_all_traces()) == 0


class TestReActAgentTracing:
    def test_react_agent_has_full_trace(self):
        """ReActAgent.run() produces trace with AGENT_RUN → AGENT_STEP → LLM_CALL."""
        llm = _mock_llm(["Thought: I know\nAction: Finish[42]"])
        agent = ReActAgent(name="test", llm=llm, config=Config(api_key="x"))
        result = agent.run("what is 6*7?")

        traces = Tracer().get_all_traces()
        assert len(traces) == 1
        root = traces[0]
        assert root.type == SpanType.AGENT_RUN
        assert root.metadata.get("run_id") is not None

        # Should have step children
        assert len(root.children) >= 1
        step = root.children[0]
        assert step.type == SpanType.AGENT_STEP

        # Step should have LLM_CALL child
        llm_spans = [c for c in step.children if c.type == SpanType.LLM_CALL]
        assert len(llm_spans) == 1

    def test_react_agent_trace_with_tool(self):
        """ReActAgent with tool call produces TOOL_CALL span."""
        llm = _mock_llm([
            "Thought: need calc\nAction: Calculator[2+3]",
            "Thought: done\nAction: Finish[5]",
        ])
        registry = ToolRegistry()
        registry.register_function(
            "calculator", "calc", lambda args: str(eval(args.get("expression", "0")))
        )
        agent = ReActAgent(
            name="test", llm=llm, config=Config(api_key="x"),
            tool_registry=registry,
        )
        result = agent.run("2+3?")

        all_spans = _flatten(Tracer().get_all_traces()[0])
        tool_spans = [s for s in all_spans if s.type == SpanType.TOOL_CALL]
        assert len(tool_spans) == 1
        assert tool_spans[0].input is not None

    def test_react_agent_trace_error_on_parse_failure(self):
        """ReActAgent records parse failure as event, not error span."""
        llm = _mock_llm([
            "no valid format here",
            "Thought: ok\nAction: Finish[done]",
        ])
        agent = ReActAgent(name="test", llm=llm, config=Config(api_key="x"))
        result = agent.run("hi")

        root = Tracer().get_all_traces()[0]
        step = root.children[0]
        assert step.status == SpanStatus.OK  # step itself is OK, error is just an event

    def test_react_agent_trace_contains_token_stats(self):
        """Trace contains token usage in LLM_CALL spans."""
        llm = _mock_llm(["Thought: ok\nAction: Finish[answer]"])
        agent = ReActAgent(name="test", llm=llm, config=Config(api_key="x"))
        agent.run("hi")

        all_spans = _flatten(Tracer().get_all_traces()[0])
        llm_spans = [s for s in all_spans if s.type == SpanType.LLM_CALL]
        assert llm_spans[0].metadata["token_usage"]["prompt"] == 100

    def test_react_agent_tracing_disabled(self):
        """When enable_tracing=False, no traces produced."""
        llm = _mock_llm(["Thought: ok\nAction: Finish[answer]"])
        agent = ReActAgent(
            name="test", llm=llm, config=Config(api_key="x"),
            enable_tracing=False,
        )
        agent.run("hi")
        assert len(Tracer().get_all_traces()) == 0


def _flatten(span) -> list:
    """Recursively collect all spans into a flat list."""
    result = [span]
    for child in span.children:
        result.extend(_flatten(child))
    return result
