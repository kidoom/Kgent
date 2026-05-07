"""Tests for LLM Provider abstraction and registry"""

import pytest
from typing import Iterator

from kagent.core.llm import (
    LLMResponse,
    LLMChunk,
    LLMProvider,
    LLMProviderRegistry,
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
