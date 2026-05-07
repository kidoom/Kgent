"""Integration tests: Stage A — LLM ↔ Tool wiring"""

import os
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from kagent.core.config import Config
from kagent.core.llm import (
    LLMResponse,
    LLMChunk,
    LLMProvider,
    LLMProviderRegistry,
    AgentLLM,
    OpenAIProvider,
)
from kagent.tools.base import Tool, ToolResult, ToolParameter
from kagent.tools.registry import ToolRegistry
from kagent.tools.builtin.calculator import CalculatorTool
from kagent.tools.builtin.search import SearchTool


class EchoTool(Tool):
    """Simple echo tool for integration testing"""

    def __init__(self):
        super().__init__(name="echo", description="Echoes the input text")

    def run(self, parameters: dict) -> ToolResult:
        text = parameters.get("text", "")
        return ToolResult(content=text, success=True)

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="text", type="string",
                description="Text to echo", required=True,
            )
        ]


# ── AgentLLM + ToolRegistry wire ──────────────────────────────────────

class TestAgentLLMWithToolRegistry:
    """AgentLLM initialized → ToolRegistry populated → tools executable"""

    def test_agent_llm_configured_correctly(self):
        """AgentLLM reads Config, provider + tool registry work independently"""
        config = Config(
            default_provider="openai",
            default_model="gpt-4o",
            api_key="sk-test",
        )

        # Register a mock provider
        provider = MagicMock(spec=LLMProvider)
        AgentLLM.register_provider("openai", provider)

        llm = AgentLLM(config=config)
        assert llm.provider_name == "openai"
        assert llm.model == "gpt-4o"
        assert llm._provider is provider

        # Tool registry works independently
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        result = registry.execute_tool("calculator", {"expression": "2+3"})
        assert result.success is True
        assert result.content == "5"

    def test_tool_registry_full_lifecycle(self):
        """Register → execute → disable → execute → enable → unregister"""
        registry = ToolRegistry()
        registry.register_tool(EchoTool())
        registry.register_function("upper", "Convert to uppercase", lambda a: a.get("text", "").upper())

        # Execute both
        assert registry.execute_tool("echo", {"text": "hello"}).content == "hello"
        assert registry.execute_tool("upper", {"text": "hello"}).content == "HELLO"

        # Disable echo
        registry.disable("echo")
        assert registry.execute_tool("echo", {"text": "x"}).success is False
        assert registry.execute_tool("upper", {"text": "x"}).success is True

        # Enable echo
        registry.enable("echo")
        assert registry.execute_tool("echo", {"text": "hello again"}).content == "hello again"

        # List tools
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tools["echo"]["enabled"] is True
        assert tools["upper"]["enabled"] is True

        # Unregister
        registry.unregister("echo")
        assert registry.execute_tool("echo", {"text": "x"}).success is False

    def test_mock_llm_with_tool_call_flow(self):
        """Simulate Agent → LLM → tool_call → execute_tool flow"""
        config = Config(api_key="sk-test")

        # Mock LLM that returns a tool call
        mock_response = LLMResponse(
            content="",
            tool_calls=[{
                "id": "call_1",
                "function": {
                    "name": "calculator",
                    "arguments": '{"expression": "6*7"}',
                },
            }],
        )

        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.chat.return_value = mock_response

        AgentLLM._registry = LLMProviderRegistry()
        AgentLLM.register_provider("openai", mock_provider)

        # AgentLLM invokes → receives tool_call
        llm = AgentLLM(config=config)
        response = llm.invoke([{"role": "user", "content": "calc 6*7"}])

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["function"]["name"] == "calculator"

        # ToolRegistry executes the tool call
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        result = registry.execute_tool(
            "calculator",
            {"expression": "6*7"},
        )
        assert result.success is True
        assert result.content == "42"


# ── Provider switch ────────────────────────────────────────────────────

class TestProviderSwitch:
    """Verify that switching provider name changes the underlying instance"""

    def test_switch_provider_at_runtime(self):
        """Two providers → switch name → different instance used"""
        config = Config(api_key="sk-test")

        mock_openai = MagicMock(spec=LLMProvider)
        mock_ollama = MagicMock(spec=LLMProvider)

        AgentLLM._registry = LLMProviderRegistry()
        AgentLLM.register_provider("openai", mock_openai)
        AgentLLM.register_provider("ollama", mock_ollama)

        llm_openai = AgentLLM(provider="openai", config=config)
        assert llm_openai._provider is mock_openai

        llm_ollama = AgentLLM(provider="ollama", config=config)
        assert llm_ollama._provider is mock_ollama

    def test_provider_switch_via_config(self):
        """Config drives provider selection"""
        mock_openai = MagicMock(spec=LLMProvider)
        mock_ollama = MagicMock(spec=LLMProvider)

        AgentLLM._registry = LLMProviderRegistry()
        AgentLLM.register_provider("openai", mock_openai)
        AgentLLM.register_provider("ollama", mock_ollama)

        config_openai = Config(default_provider="openai", api_key="sk-test")
        llm = AgentLLM(config=config_openai)
        assert llm._provider is mock_openai

        config_ollama = Config(default_provider="ollama")
        llm = AgentLLM(config=config_ollama)
        assert llm._provider is mock_ollama


# ── OpenAIProvider integration (mocked API) ────────────────────────────

class TestOpenAIProviderIntegration:
    """OpenAIProvider with tool schemas via mocked API"""

    def test_chat_passes_tools_to_api(self):
        """OpenAIProvider forwards tool definitions to the API"""
        mock_msg = MagicMock()
        mock_msg.content = "I'll use the calculator"
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        calc = CalculatorTool()
        tools = [calc.to_openai_schema()]

        with patch("openai.OpenAI", return_value=mock_client):
            provider = OpenAIProvider(
                api_key="sk-test",
                base_url="https://api.openai.com/v1",
            )
            response = provider.chat(
                messages=[{"role": "user", "content": "calc 2+2"}],
                model="gpt-4o",
                temperature=0.0,
                tools=tools,
            )

        assert response.content == "I'll use the calculator"
        # Verify the API was called with tools
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1
        assert call_kwargs["tools"][0]["function"]["name"] == "calculator"


# ── Complete A-stage smoke test ────────────────────────────────────────

class TestStageASmoke:
    """End-to-end smoke: Config → AgentLLM → OpenAIProvider → ToolRegistry"""

    def test_full_wire_no_real_api(self):
        """All A-stage components connected without real API calls"""
        # 1. Config
        config = Config(
            default_provider="openai",
            default_model="gpt-4o",
            api_key="sk-test",
        )

        # 2. OpenAIProvider with mocked API
        mock_msg = MagicMock()
        mock_msg.content = "42"
        mock_msg.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_msg

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = MagicMock()
        mock_completion.usage.prompt_tokens = 10
        mock_completion.usage.completion_tokens = 1
        mock_completion.usage.total_tokens = 11

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch("openai.OpenAI", return_value=mock_client):
            provider = OpenAIProvider(
                api_key=config.api_key,
                base_url="https://api.openai.com/v1",
            )
            AgentLLM._registry = LLMProviderRegistry()
            AgentLLM.register_provider("openai", provider)

            # 3. AgentLLM invoke
            llm = AgentLLM(config=config)
            response = llm.invoke([{"role": "user", "content": "What is 6*7?"}])
            assert response.content == "42"
            assert response.usage["total"] == 11

        # 4. ToolRegistry with real CalculatorTool
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        registry.register_tool(SearchTool())

        calc_result = registry.execute_tool("calculator", {"expression": "6*7"})
        assert calc_result.content == "42"

        # Search fails without API key (graceful degradation)
        with patch.dict(os.environ, {"SERPAPI_API_KEY": "", "TAVILY_API_KEY": ""}, clear=True):
            search_result = registry.execute_tool("search", {"query": "Python"})
            assert search_result.success is False
            assert "未配置" in search_result.content

        # 5. Tool management
        assert registry.is_enabled("calculator") is True
        registry.disable("calculator")
        assert registry.is_enabled("calculator") is False
        assert registry.list_tools()["calculator"]["enabled"] is False
        assert "calculator" not in registry.get_tools_description()
