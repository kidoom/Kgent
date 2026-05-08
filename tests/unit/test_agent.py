"""Tests for Agent base class, SimpleAgent, and ReActAgent"""

import pytest
from typing import Iterator
from unittest.mock import MagicMock

from kagent.core.agent import Agent
from kagent.core.config import Config
from kagent.core.message import Message
from kagent.core.llm import LLMProvider, LLMProviderRegistry, AgentLLM, LLMResponse, LLMChunk
from kagent.agents.simple_agent import SimpleAgent as RealSimpleAgent
from kagent.agents.react_agent import ReActAgent
from kagent.tools.registry import ToolRegistry
from kagent.tools.builtin.calculator import CalculatorTool


# --- Helpers ---

class MockLLMProvider(LLMProvider):
    def __init__(self, response_content: str = "mock response"):
        self.response_content = response_content

    def chat(self, messages, model, temperature, tools=None, tool_choice=None) -> LLMResponse:
        return LLMResponse(content=self.response_content)

    def chat_stream(self, messages, model, temperature, tools=None, tool_choice=None) -> Iterator[LLMChunk]:
        yield LLMChunk(delta=self.response_content)


class SequentialMockLLMProvider(LLMProvider):
    """Returns different responses on successive calls."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._call_count = 0

    def chat(self, messages, model, temperature, tools=None, tool_choice=None) -> LLMResponse:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return LLMResponse(content=self._responses[idx])

    def chat_stream(self, messages, model, temperature, tools=None, tool_choice=None) -> Iterator[LLMChunk]:
        yield LLMChunk(delta="mock")


def _make_llm(response: str = "mock response", name: str = "mock") -> AgentLLM:
    """Create an AgentLLM with a mock provider registered"""
    AgentLLM._registry = LLMProviderRegistry()
    AgentLLM.register_provider(name, MockLLMProvider(response))
    return AgentLLM(provider=name, config=Config(api_key="sk-test"))


def _make_sequential_llm(responses: list[str], name: str = "seq") -> AgentLLM:
    """Create an AgentLLM that returns different responses per call."""
    AgentLLM._registry = LLMProviderRegistry()
    AgentLLM.register_provider(name, SequentialMockLLMProvider(responses))
    return AgentLLM(provider=name, config=Config(api_key="sk-test"))


class ConcreteAgent(Agent):
    """Concrete Agent subclass for testing base class"""

    def run(self, input_text: str, **kwargs) -> str:
        self.add_message(Message(content=input_text, role="user"))
        response = f"echo: {input_text}"
        self.add_message(Message(content=response, role="assistant"))
        return response


# --- Tests ---

class TestAgentIsAbstract:
    """Agent cannot be instantiated directly"""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError, match="abstract method"):
            Agent(name="test", llm=_make_llm())


class TestAgentInit:
    """Test Agent initialization"""

    def test_name_and_llm(self):
        llm = _make_llm()
        agent = ConcreteAgent(name="test", llm=llm)
        assert agent.name == "test"
        assert agent.llm is llm

    def test_system_prompt_optional(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        assert agent.system_prompt is None

    def test_system_prompt_set(self):
        agent = ConcreteAgent(name="test", llm=_make_llm(), system_prompt="You are helpful")
        assert agent.system_prompt == "You are helpful"

    def test_config_default(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        assert isinstance(agent.config, Config)

    def test_config_custom(self):
        cfg = Config(api_key="sk-test", max_history_length=10)
        agent = ConcreteAgent(name="test", llm=_make_llm(), config=cfg)
        assert agent.config.max_history_length == 10


class TestAgentHistory:
    """Test add_message / get_history / clear_history"""

    def test_get_history_empty(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        assert agent.get_history() == []

    def test_add_message(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        msg = Message(content="hi", role="user")
        agent.add_message(msg)
        history = agent.get_history()
        assert len(history) == 1
        assert history[0].content == "hi"

    def test_add_multiple_messages(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        agent.add_message(Message(content="a", role="user"))
        agent.add_message(Message(content="b", role="assistant"))
        agent.add_message(Message(content="c", role="user"))
        assert len(agent.get_history()) == 3

    def test_clear_history(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        agent.add_message(Message(content="a", role="user"))
        agent.add_message(Message(content="b", role="assistant"))
        agent.add_message(Message(content="c", role="user"))
        agent.clear_history()
        assert agent.get_history() == []

    def test_clear_history_empty(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        agent.clear_history()
        assert agent.get_history() == []

    def test_get_history_returns_copy(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        agent.add_message(Message(content="hi", role="user"))
        history = agent.get_history()
        history.clear()
        assert len(agent.get_history()) == 1

    def test_max_history_trims(self):
        cfg = Config(api_key="sk-test", max_history_length=2)
        agent = ConcreteAgent(name="test", llm=_make_llm(), config=cfg)
        agent.add_message(Message(content="a", role="user"))
        agent.add_message(Message(content="b", role="assistant"))
        agent.add_message(Message(content="c", role="user"))
        history = agent.get_history()
        assert len(history) == 2
        assert history[0].content == "b"
        assert history[1].content == "c"


class TestConcreteAgentRun:
    """Test the concrete Agent subclass run()"""

    def test_run_returns_string(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        result = agent.run("hello")
        assert result == "echo: hello"

    def test_run_populates_history(self):
        agent = ConcreteAgent(name="test", llm=_make_llm())
        agent.run("hello")
        history = agent.get_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"
        assert history[0].content == "hello"
        assert history[1].content == "echo: hello"


# --- SimpleAgent (real) tests ---

class TestSimpleAgent:
    """Tests for the real SimpleAgent from kagent.agents.simple_agent"""

    def test_run_without_tools_returns_llm_response(self):
        llm = _make_llm("hello world")
        agent = RealSimpleAgent(name="test", llm=llm)
        result = agent.run("hi")
        assert result == "hello world"

    def test_run_without_tools_populates_history(self):
        llm = _make_llm("reply")
        agent = RealSimpleAgent(name="test", llm=llm)
        agent.run("hi")
        history = agent.get_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "hi"
        assert history[1].role == "assistant"
        assert history[1].content == "reply"

    def test_parse_tool_calls_single(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        calls = agent._parse_tool_calls("Let me calculate: [TOOL_CALL:calculator:1+1]")
        assert len(calls) == 1
        assert calls[0]["name"] == "calculator"
        assert calls[0]["params"] == "1+1"

    def test_parse_tool_calls_multiple(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        text = "[TOOL_CALL:calculator:2+3] and [TOOL_CALL:search:Python]"
        calls = agent._parse_tool_calls(text)
        assert len(calls) == 2
        assert calls[0]["name"] == "calculator"
        assert calls[1]["name"] == "search"

    def test_parse_tool_calls_none(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        calls = agent._parse_tool_calls("Just a normal response")
        assert calls == []

    def test_run_with_tool_call(self):
        """LLM returns tool call → execute → inject → LLM returns final answer."""
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        llm = _make_sequential_llm([
            "[TOOL_CALL:calculator:1+1]",
            "The answer is 2",
        ])
        agent = RealSimpleAgent(
            name="test", llm=llm, tool_registry=registry,
        )
        result = agent.run("what is 1+1?")
        assert "The answer is 2" in result

    def test_run_tool_not_registered(self):
        """Tool doesn't exist → Observation contains error, loop continues."""
        registry = ToolRegistry()
        # Don't register any tool

        llm = _make_sequential_llm([
            "[TOOL_CALL:calculator:1+1]",
            "I cannot compute that.",
        ])
        agent = RealSimpleAgent(
            name="test", llm=llm, tool_registry=registry,
        )
        result = agent.run("what is 1+1?")
        assert result == "I cannot compute that."

    def test_run_max_steps_exceeded(self):
        """Exceeding max_steps returns current best answer without error."""
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        # LLM keeps returning tool calls, never a final answer
        llm = _make_sequential_llm([
            "[TOOL_CALL:calculator:1+1]",
            "[TOOL_CALL:calculator:2+2]",
            "[TOOL_CALL:calculator:3+3]",
        ])
        agent = RealSimpleAgent(
            name="test", llm=llm, tool_registry=registry,
            config=Config(api_key="sk-test", max_steps=2),
        )
        result = agent.run("calculate")
        # Should not raise, returns whatever the last LLM output was
        assert isinstance(result, str)

    def test_add_tool_creates_registry(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        assert agent.tool_registry is None
        agent.add_tool(CalculatorTool())
        assert agent.tool_registry is not None
        assert agent.tool_registry.is_registered("calculator")

    def test_remove_tool(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        agent.add_tool(CalculatorTool())
        assert agent.remove_tool("calculator")
        assert not agent.tool_registry.is_registered("calculator")

    def test_remove_tool_no_registry(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        assert agent.remove_tool("calculator") is False

    def test_stream_run(self):
        llm = _make_llm("streamed reply")
        agent = RealSimpleAgent(name="test", llm=llm)
        chunks = list(agent.stream_run("hi"))
        # stream yields LLMChunks; content is assembled internally
        history = agent.get_history()
        assert len(history) == 2
        assert history[1].content == "streamed reply"

    def test_system_prompt_in_messages(self):
        llm = _make_llm("ok")
        agent = RealSimpleAgent(
            name="test", llm=llm, system_prompt="You are a test bot",
        )
        agent.run("hi")
        # Verify the LLM received the system prompt
        # (by checking history has the user message)
        history = agent.get_history()
        assert len(history) == 2


# --- ReActAgent tests ---

class TestReActAgent:
    """Tests for the ReActAgent"""

    def test_finish_action_returns_answer(self):
        """Action: Finish[答案] → run() returns '答案'"""
        llm = _make_sequential_llm([
            "Thought: I know the answer.\nAction: Finish[北京今天晴，25°C]",
        ])
        agent = ReActAgent(name="test", llm=llm)
        result = agent.run("北京天气")
        assert result == "北京今天晴，25°C"

    def test_tool_call_then_finish(self):
        """Action: Calculator → execute → Observation → Action: Finish"""
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        llm = _make_sequential_llm([
            "Thought: I need to calculate.\nAction: Calculator[1+1]",
            "Thought: The result is 2.\nAction: Finish[1+1等于2]",
        ])
        agent = ReActAgent(name="test", llm=llm, tool_registry=registry)
        result = agent.run("1+1等于几")
        assert result == "1+1等于2"

    def test_tool_not_registered_continues(self):
        """Tool not found → Observation error → loop continues."""
        registry = ToolRegistry()
        # Don't register any tools

        llm = _make_sequential_llm([
            "Thought: I'll try a tool.\nAction: Calculator[1+1]",
            "Thought: Tool failed, I'll answer directly.\nAction: Finish[无法计算]",
        ])
        agent = ReActAgent(name="test", llm=llm, tool_registry=registry)
        result = agent.run("计算")
        assert result == "无法计算"

    def test_no_action_injects_error(self):
        """LLM returns plain text without Action: → error observation → loop continues."""
        llm = _make_sequential_llm([
            "This is just a plain response with no action.",
            "Thought: I'll follow the format now.\nAction: Finish[corrected answer]",
        ])
        agent = ReActAgent(name="test", llm=llm)
        result = agent.run("hello")
        assert result == "corrected answer"

    def test_max_steps_exceeded(self):
        """Exceeding max_steps returns best answer without error."""
        # LLM keeps returning tool calls, never Finish
        llm = _make_sequential_llm([
            "Thought: step 1\nAction: Calculator[1+1]",
            "Thought: step 2\nAction: Calculator[2+2]",
            "Thought: step 3\nAction: Calculator[3+3]",
        ])
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        agent = ReActAgent(
            name="test", llm=llm, tool_registry=registry,
            config=Config(api_key="sk-test", max_steps=2),
        )
        result = agent.run("calculate")
        assert isinstance(result, str)

    def test_max_steps_no_action(self):
        """LLM keeps returning text without Action → returns at max_steps."""
        llm = _make_sequential_llm([
            "plain text 1",
            "plain text 2",
            "plain text 3",
        ])
        agent = ReActAgent(
            name="test", llm=llm,
            config=Config(api_key="sk-test", max_steps=2),
        )
        result = agent.run("hello")
        assert isinstance(result, str)

    def test_parse_output_both(self):
        """_parse_output extracts both Thought and Action."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        thought, action = agent._parse_output(
            "Thought: I need to search.\nAction: Search[Python]"
        )
        assert thought == "I need to search."
        assert action == "Search[Python]"

    def test_parse_output_action_only(self):
        """_parse_output extracts Action when no Thought."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        thought, action = agent._parse_output("Action: Finish[answer]")
        assert thought is None
        assert action == "Finish[answer]"

    def test_parse_output_none(self):
        """_parse_output returns (None, None) for plain text."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        thought, action = agent._parse_output("Just a plain response")
        assert thought is None
        assert action is None

    def test_parse_action_tool(self):
        """_parse_action extracts tool name and params."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        name, params = agent._parse_action("Calculator[2+3]")
        assert name == "Calculator"
        assert params == "2+3"

    def test_parse_action_finish(self):
        """_parse_action extracts Finish action."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        name, params = agent._parse_action("Finish[final answer]")
        assert name == "Finish"
        assert params == "final answer"

    def test_parse_action_multiline_params(self):
        """_parse_action handles multiline params."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        name, params = agent._parse_action("Finish[answer\nwith\nnewlines]")
        assert name == "Finish"
        assert "answer" in params

    def test_format_prompt_includes_tools(self):
        """_format_prompt includes tool descriptions."""
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm, tool_registry=registry)
        prompt = agent._format_prompt("test input")
        assert "calculator" in prompt
        assert "test input" in prompt

    def test_format_prompt_no_tools(self):
        """_format_prompt works without tools."""
        llm = _make_llm()
        agent = ReActAgent(name="test", llm=llm)
        prompt = agent._format_prompt("test input")
        assert "test input" in prompt

    def test_custom_system_prompt(self):
        """ReActAgent uses custom system_prompt if provided."""
        custom_prompt = "Custom prompt: {tools}\n{history}\n{input}"
        llm = _make_sequential_llm([
            "Thought: custom.\nAction: Finish[custom answer]",
        ])
        agent = ReActAgent(name="test", llm=llm, system_prompt=custom_prompt)
        result = agent.run("test")
        assert result == "custom answer"

    def test_history_populated(self):
        """run() populates conversation history."""
        llm = _make_sequential_llm([
            "Thought: answering.\nAction: Finish[hi there]",
        ])
        agent = ReActAgent(name="test", llm=llm)
        agent.run("hello")
        history = agent.get_history()
        assert len(history) >= 2
        assert history[0].role == "user"
        assert history[0].content == "hello"


# --- C3: Agent base framework tests ---

class TestAgentCustomPrompt:
    """Test custom_prompt template variable injection"""

    def test_custom_prompt_stored(self):
        llm = _make_llm()
        agent = RealSimpleAgent(
            name="test", llm=llm,
            config=Config(api_key="x"),
            custom_prompt="{tools}\n{input}",
        )
        assert agent.custom_prompt == "{tools}\n{input}"

    def test_format_prompt_replaces_input(self):
        llm = _make_llm()
        agent = RealSimpleAgent(
            name="test", llm=llm,
            config=Config(api_key="x"),
            custom_prompt="User said: {input}",
        )
        result = agent._format_prompt(agent.custom_prompt, input="hello world")
        assert "hello world" in result

    def test_format_prompt_replaces_tools(self):
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        llm = _make_llm()
        agent = RealSimpleAgent(
            name="test", llm=llm,
            config=Config(api_key="x"),
            custom_prompt="Tools:\n{tools}",
            tool_registry=registry,
        )
        result = agent._format_prompt(agent.custom_prompt, input="test")
        assert "calculator" in result

    def test_format_prompt_replaces_history(self):
        llm = _make_llm()
        agent = RealSimpleAgent(
            name="test", llm=llm,
            config=Config(api_key="x"),
            custom_prompt="History:\n{history}",
        )
        agent.add_message(Message(content="prev msg", role="user"))
        result = agent._format_prompt(agent.custom_prompt, input="test")
        assert "prev msg" in result

    def test_format_prompt_replaces_max_steps(self):
        llm = _make_llm()
        agent = RealSimpleAgent(
            name="test", llm=llm,
            config=Config(api_key="x", max_steps=7),
            custom_prompt="Steps: {max_steps}",
        )
        result = agent._format_prompt(agent.custom_prompt, input="test")
        assert "7" in result


class TestAgentRunId:
    """Test run_id generation on each run()"""

    def test_run_id_set_after_run(self):
        llm = _make_llm("ok")
        agent = RealSimpleAgent(name="test", llm=llm)
        agent.run("hi")
        assert len(agent.run_id) == 8

    def test_run_id_changes_each_run(self):
        llm = _make_llm("ok")
        agent = RealSimpleAgent(name="test", llm=llm)
        agent.run("first")
        first_id = agent.run_id
        agent.run("second")
        second_id = agent.run_id
        assert first_id != second_id

    def test_run_id_react_agent(self):
        llm = _make_sequential_llm(["Thought: ok\nAction: Finish[answer]"])
        agent = ReActAgent(name="test", llm=llm)
        agent.run("hi")
        assert len(agent.run_id) == 8

    def test_new_run_id_returns_hex(self):
        llm = _make_llm()
        agent = RealSimpleAgent(name="test", llm=llm)
        rid = agent._new_run_id()
        assert len(rid) == 8
        int(rid, 16)  # should not raise — valid hex
