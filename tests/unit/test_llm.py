"""Tests for LLM Provider abstraction and registry"""

import os
import pytest
from typing import Iterator
from unittest.mock import patch, MagicMock

from kagent.core.config import Config, ConfigError
from kagent.core.exceptions import LLMError
from kagent.core.llm import (
    LLMResponse,
    LLMChunk,
    LLMProvider,
    LLMProviderRegistry,
    AgentLLM,
    OpenAIProvider,
)


# Mock provider for testing
class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing"""

    def __init__(self, response_content: str = "mock response"):
        self.response_content = response_content

    def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        tools=None,
        tool_choice=None,
    ) -> LLMResponse:
        return LLMResponse(content=self.response_content)

    def chat_stream(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        tools=None,
        tool_choice=None,
    ) -> Iterator[LLMChunk]:
        yield LLMChunk(delta="Hello")
        yield LLMChunk(delta=" World")


class TestLLMResponse:
    """Test LLMResponse model"""

    def test_create_response(self):
        resp = LLMResponse(content="test")
        assert resp.content == "test"
        assert resp.tool_calls == []
        assert resp.usage is None
        assert resp.raw is None

    def test_response_with_usage(self):
        usage = {"prompt": 10, "completion": 20, "total": 30}
        resp = LLMResponse(content="test", usage=usage)
        assert resp.usage == usage

    def test_response_with_tool_calls(self):
        tool_calls = [{"id": "call_1", "function": {"name": "test"}}]
        resp = LLMResponse(content="", tool_calls=tool_calls)
        assert len(resp.tool_calls) == 1


class TestLLMChunk:
    """Test LLMChunk model"""

    def test_create_chunk(self):
        chunk = LLMChunk(delta="hello")
        assert chunk.delta == "hello"
        assert chunk.usage is None

    def test_chunk_with_usage(self):
        usage = {"prompt": 5, "completion": 10, "total": 15}
        chunk = LLMChunk(delta="test", usage=usage)
        assert chunk.usage == usage


class TestLLMProviderIsAbstract:
    """Test LLMProvider cannot be instantiated"""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError, match="abstract method"):
            LLMProvider()

    def test_subclass_must_implement_chat(self):
        class IncompleteProvider(LLMProvider):
            pass

        with pytest.raises(TypeError, match="abstract method"):
            IncompleteProvider()

    def test_subclass_with_chat_only_still_abstract(self):
        class PartialProvider(LLMProvider):
            def chat(self, messages, model, temperature, tools=None, tool_choice=None):
                return LLMResponse(content="test")

        with pytest.raises(TypeError, match="abstract method"):
            PartialProvider()

    def test_subclass_with_all_methods_works(self):
        provider = MockLLMProvider()
        assert isinstance(provider, LLMProvider)


class TestLLMProviderRegistry:
    """Test LLMProviderRegistry"""

    def test_register_and_get(self):
        registry = LLMProviderRegistry()
        provider = MockLLMProvider()
        registry.register("test", provider)
        assert registry.get("test") is provider

    def test_get_nonexistent_raises(self):
        registry = LLMProviderRegistry()
        with pytest.raises(ValueError, match="not registered"):
            registry.get("nonexistent")

    def test_list_providers_empty(self):
        registry = LLMProviderRegistry()
        assert registry.list_providers() == []

    def test_list_providers_multiple(self):
        registry = LLMProviderRegistry()
        registry.register("mock1", MockLLMProvider("response1"))
        registry.register("mock2", MockLLMProvider("response2"))
        providers = registry.list_providers()
        assert len(providers) == 2
        assert "mock1" in providers
        assert "mock2" in providers

    def test_register_non_provider_raises(self):
        registry = LLMProviderRegistry()
        with pytest.raises(TypeError, match="Expected LLMProvider"):
            registry.register("bad", "not a provider")

    def test_register_overwrites(self):
        registry = LLMProviderRegistry()
        provider1 = MockLLMProvider("first")
        provider2 = MockLLMProvider("second")
        registry.register("test", provider1)
        registry.register("test", provider2)
        assert registry.get("test") is provider2

    def test_provider_chat(self):
        provider = MockLLMProvider("hello from mock")
        resp = provider.chat(
            messages=[{"role": "user", "content": "hi"}],
            model="test-model",
            temperature=0.0,
        )
        assert resp.content == "hello from mock"

    def test_provider_chat_stream(self):
        provider = MockLLMProvider()
        chunks = list(
            provider.chat_stream(
                messages=[{"role": "user", "content": "hi"}],
                model="test-model",
                temperature=0.0,
            )
        )
        assert len(chunks) == 2
        assert chunks[0].delta == "Hello"
        assert chunks[1].delta == " World"


class TestAgentLLMInit:
    """Test AgentLLM initialization"""

    def setup_method(self):
        """Clean up AgentLLM registry before each test"""
        AgentLLM._registry = LLMProviderRegistry()

    def _config(self, **kwargs):
        """Create a Config instance with defaults for testing"""
        defaults = {
            "default_provider": "openai",
            "default_model": "gpt-4o",
            "api_key": "sk-test",
        }
        defaults.update(kwargs)
        return Config(**defaults)

    def test_init_with_explicit_provider(self):
        """Test explicit provider name"""
        AgentLLM.register_provider("mock", MockLLMProvider())
        config = self._config()
        llm = AgentLLM(provider="mock", config=config)
        assert llm.provider_name == "mock"

    def test_init_from_config(self):
        """Test reading provider from Config"""
        AgentLLM.register_provider("testenv", MockLLMProvider())
        config = self._config(default_provider="testenv", default_model="test-model")
        llm = AgentLLM(config=config)
        assert llm.provider_name == "testenv"
        assert llm.model == "test-model"

    def test_init_default_provider(self):
        """Test default provider is openai from Config"""
        AgentLLM.register_provider("openai", MockLLMProvider())
        config = self._config()
        llm = AgentLLM(config=config)
        assert llm.provider_name == "openai"

    def test_init_api_key_from_config(self):
        """Test api_key is read from Config"""
        AgentLLM.register_provider("openai", MockLLMProvider())
        config = self._config(api_key="sk-from-config")
        llm = AgentLLM(config=config)
        assert llm.api_key == "sk-from-config"

    def test_init_base_url_from_config(self):
        """Test base_url is read from Config"""
        AgentLLM.register_provider("openai", MockLLMProvider())
        config = self._config(base_url="https://custom.api.com/v1")
        llm = AgentLLM(config=config)
        assert llm.base_url == "https://custom.api.com/v1"

    def test_init_explicit_overrides_config(self):
        """Test explicit params override Config"""
        AgentLLM.register_provider("openai", MockLLMProvider())
        config = self._config(api_key="from-config", default_model="from-config")
        llm = AgentLLM(
            provider="openai",
            api_key="explicit-key",
            model="explicit-model",
            config=config,
        )
        assert llm.api_key == "explicit-key"
        assert llm.model == "explicit-model"

    def test_init_unregistered_provider_raises(self):
        """Test unregistered provider raises ConfigError"""
        config = self._config()
        with pytest.raises(ConfigError, match="not registered"):
            AgentLLM(provider="nonexistent", config=config)

    def test_register_provider_classmethod(self):
        """Test register_provider classmethod"""
        provider = MockLLMProvider("custom response")
        AgentLLM.register_provider("custom", provider)
        config = self._config()
        llm = AgentLLM(provider="custom", config=config)
        assert llm._provider is provider

    def test_init_lazy_loads_openai_provider(self):
        """Test provider is lazy-loaded from PROVIDER_CONFIG when not pre-registered."""
        mock_msg = MagicMock()
        mock_msg.content = "lazy loaded"
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch("openai.OpenAI", return_value=mock_client):
            llm = AgentLLM(config=self._config())
            resp = llm.invoke([{"role": "user", "content": "hello"}])
            assert resp.content == "lazy loaded"


class TestAgentLLMInvoke:
    """Test AgentLLM.invoke()"""

    def setup_method(self):
        """Clean up and register mock provider"""
        AgentLLM._registry = LLMProviderRegistry()
        AgentLLM.register_provider("mock", MockLLMProvider("invoke response"))

    def _config(self):
        """Create a Config instance for testing"""
        return Config(api_key="sk-test")

    def test_invoke_returns_response(self):
        config = self._config()
        llm = AgentLLM(provider="mock", config=config)
        resp = llm.invoke([{"role": "user", "content": "hi"}])
        assert resp.content == "invoke response"

    def test_invoke_passes_model(self):
        config = self._config()
        llm = AgentLLM(provider="mock", model="custom-model", config=config)
        assert llm.model == "custom-model"

    def test_stream_yields_chunks(self):
        config = self._config()
        llm = AgentLLM(provider="mock", config=config)
        chunks = list(llm.stream([{"role": "user", "content": "hi"}]))
        assert len(chunks) == 2
        assert chunks[0].delta == "Hello"
        assert chunks[1].delta == " World"


class TestOpenAIProvider:
    """Test OpenAIProvider with mocked OpenAI SDK"""

    def provider(self):
        return OpenAIProvider(
            api_key="sk-test", base_url="https://api.openai.com/v1"
        )

    def test_chat_returns_response(self):
        """Test chat returns LLMResponse with mocked OpenAI"""
        mock_msg = MagicMock()
        mock_msg.content = "hello from openai"
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = MagicMock()
        mock_completion.usage.prompt_tokens = 10
        mock_completion.usage.completion_tokens = 5
        mock_completion.usage.total_tokens = 15

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch("openai.OpenAI", return_value=mock_client):
            provider = self.provider()
            resp = provider.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-4o",
                temperature=0.0,
            )

        assert resp.content == "hello from openai"
        assert resp.usage == {"prompt": 10, "completion": 5, "total": 15}

    def test_chat_with_tool_calls(self):
        """Test chat extracts tool_calls correctly"""
        mock_tc = MagicMock()
        mock_tc.id = "call_1"
        mock_tc.function.name = "test_tool"
        mock_tc.function.arguments = '{"arg": "value"}'

        mock_msg = MagicMock()
        mock_msg.content = ""
        mock_msg.tool_calls = [mock_tc]

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch("openai.OpenAI", return_value=mock_client):
            provider = self.provider()
            resp = provider.chat(
                messages=[{"role": "user", "content": "call test_tool"}],
                model="gpt-4o",
                temperature=0.0,
            )

        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["id"] == "call_1"
        assert resp.tool_calls[0]["function"]["name"] == "test_tool"

    def test_chat_stream_yields_chunks(self):
        """Test chat_stream yields LLMChunks"""
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk1.usage = None

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " World"
        chunk2.usage = MagicMock()
        chunk2.usage.prompt_tokens = 10
        chunk2.usage.completion_tokens = 5
        chunk2.usage.total_tokens = 15

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2]

        with patch("openai.OpenAI", return_value=mock_client):
            provider = self.provider()
            chunks = list(
                provider.chat_stream(
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o",
                    temperature=0.0,
                )
            )

        assert len(chunks) == 2
        assert chunks[0].delta == "Hello"
        assert chunks[1].delta == " World"
        assert chunks[1].usage == {"prompt": 10, "completion": 5, "total": 15}

    def test_chat_api_error_raises_llm_error(self):
        """Test API error raises LLMError"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection timeout")

        with patch("openai.OpenAI", return_value=mock_client):
            provider = self.provider()
            with pytest.raises(LLMError, match="Connection timeout"):
                provider.chat(
                    messages=[{"role": "user", "content": "hi"}],
                    model="gpt-4o",
                    temperature=0.0,
                )
