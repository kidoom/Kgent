"""Tests for Agent base class"""

import pytest
from typing import Iterator
from unittest.mock import MagicMock

from kagent.core.agent import Agent
from kagent.core.config import Config
from kagent.core.message import Message
from kagent.core.llm import LLMProvider, LLMProviderRegistry, AgentLLM, LLMResponse, LLMChunk


# --- Helpers ---

class MockLLMProvider(LLMProvider):
    def __init__(self, response_content: str = "mock response"):
        self.response_content = response_content

    def chat(self, messages, model, temperature, tools=None, tool_choice=None) -> LLMResponse:
        return LLMResponse(content=self.response_content)

    def chat_stream(self, messages, model, temperature, tools=None, tool_choice=None) -> Iterator[LLMChunk]:
        yield LLMChunk(delta="mock")


def _make_llm(name: str = "mock") -> AgentLLM:
    """Create an AgentLLM with a mock provider registered"""
    AgentLLM._registry = LLMProviderRegistry()
    AgentLLM.register_provider(name, MockLLMProvider())
    return AgentLLM(provider=name, config=Config(api_key="sk-test"))


class SimpleAgent(Agent):
    """Concrete Agent subclass for testing"""

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
        agent = SimpleAgent(name="test", llm=llm)
        assert agent.name == "test"
        assert agent.llm is llm

    def test_system_prompt_optional(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        assert agent.system_prompt is None

    def test_system_prompt_set(self):
        agent = SimpleAgent(name="test", llm=_make_llm(), system_prompt="You are helpful")
        assert agent.system_prompt == "You are helpful"

    def test_config_default(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        assert isinstance(agent.config, Config)

    def test_config_custom(self):
        cfg = Config(api_key="sk-test", max_history_length=10)
        agent = SimpleAgent(name="test", llm=_make_llm(), config=cfg)
        assert agent.config.max_history_length == 10


class TestAgentHistory:
    """Test add_message / get_history / clear_history"""

    def test_get_history_empty(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        assert agent.get_history() == []

    def test_add_message(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        msg = Message(content="hi", role="user")
        agent.add_message(msg)
        history = agent.get_history()
        assert len(history) == 1
        assert history[0].content == "hi"

    def test_add_multiple_messages(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        agent.add_message(Message(content="a", role="user"))
        agent.add_message(Message(content="b", role="assistant"))
        agent.add_message(Message(content="c", role="user"))
        assert len(agent.get_history()) == 3

    def test_clear_history(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        agent.add_message(Message(content="a", role="user"))
        agent.add_message(Message(content="b", role="assistant"))
        agent.add_message(Message(content="c", role="user"))
        agent.clear_history()
        assert agent.get_history() == []

    def test_clear_history_empty(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        agent.clear_history()
        assert agent.get_history() == []

    def test_get_history_returns_copy(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        agent.add_message(Message(content="hi", role="user"))
        history = agent.get_history()
        history.clear()
        assert len(agent.get_history()) == 1

    def test_max_history_trims(self):
        cfg = Config(api_key="sk-test", max_history_length=2)
        agent = SimpleAgent(name="test", llm=_make_llm(), config=cfg)
        agent.add_message(Message(content="a", role="user"))
        agent.add_message(Message(content="b", role="assistant"))
        agent.add_message(Message(content="c", role="user"))
        history = agent.get_history()
        assert len(history) == 2
        assert history[0].content == "b"
        assert history[1].content == "c"


class TestSimpleAgentRun:
    """Test the concrete SimpleAgent.run()"""

    def test_run_returns_string(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        result = agent.run("hello")
        assert result == "echo: hello"

    def test_run_populates_history(self):
        agent = SimpleAgent(name="test", llm=_make_llm())
        agent.run("hello")
        history = agent.get_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"
        assert history[0].content == "hello"
        assert history[1].content == "echo: hello"
