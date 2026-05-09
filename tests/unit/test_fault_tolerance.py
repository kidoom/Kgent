"""D7 fault tolerance tests: ToolRegistry locking, LLM retry, SearchTool cache."""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch

from kagent.tools.base import Tool, ToolResult, ToolParameter
from kagent.tools.registry import ToolRegistry
from kagent.tools.builtin.search import SearchTool


class TestToolRegistryLocking:
    """T5: register/unregister/disable/enable are thread-safe."""

    def test_concurrent_register_unregister(self):
        """Concurrent register and unregister does not corrupt state."""
        registry = ToolRegistry()
        errors = []

        def register_tools():
            for i in range(50):
                registry.register_function(f"tool_{i}", f"desc_{i}", lambda a: "ok")

        def unregister_tools():
            for i in range(50):
                registry.unregister(f"tool_{i}")

        t1 = threading.Thread(target=register_tools)
        t2 = threading.Thread(target=unregister_tools)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # No crash = success. Some tools may or may not exist.
        assert isinstance(registry.list_tools(), dict)

    def test_concurrent_execute_snapshot(self):
        """execute_tool takes an immutable snapshot — unregistering mid-flight is safe."""
        registry = ToolRegistry()
        registry.register_function("echo", "echo", lambda a: a.get("query", ""))

        results = []
        errors = []

        def execute():
            for _ in range(50):
                r = registry.execute_tool("echo", {"query": "hi"})
                results.append(r)

        def unregister_later():
            time.sleep(0.01)
            registry.unregister("echo")

        t1 = threading.Thread(target=execute)
        t2 = threading.Thread(target=unregister_later)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # All results should be ToolResult (success or not_found), never an exception
        assert all(isinstance(r, ToolResult) for r in results)


class TestToolErrorReturnsString:
    """T3: Tool throwing exception → execute_tool returns ToolResult(success=False)."""

    def test_tool_error_returns_string(self):
        """Tool raises ValueError → execute_tool returns [ERROR] string, never raises."""
        registry = ToolRegistry()

        class BadTool(Tool):
            def __init__(self):
                super().__init__("bad", "broken tool")

            def run(self, parameters):
                raise ValueError("something broke")

            def get_parameters(self):
                return []

        registry.register_tool(BadTool())
        result = registry.execute_tool("bad", {})
        assert result.success is False
        assert "[ERROR]" in result.content
        assert "something broke" in result.content


class TestSearchIdempotentCache:
    """I1: Same query within 5s returns cached result — HTTP called once."""

    def test_search_cache_hit(self):
        """Same query twice → second is cached, API called once."""
        tool = SearchTool()

        # Mock the backend to count calls
        call_count = {"n": 0}
        original_run = tool.run

        def mock_search_tavily(api_key, query):
            call_count["n"] += 1
            return ToolResult(content=f"result for {query}", success=True)

        tool._search_tavily = mock_search_tavily
        tool._backend = "tavily"

        with patch.object(tool, '_get_api_key', return_value="fake-key"):
            r1 = tool.run({"query": "Python"})
            r2 = tool.run({"query": "Python"})

        assert r1.content == r2.content
        assert call_count["n"] == 1  # Only one actual API call

    def test_search_cache_miss_after_ttl(self):
        """Same query after TTL → cache miss, API called twice."""
        tool = SearchTool()
        call_count = {"n": 0}

        def mock_search_tavily(api_key, query):
            call_count["n"] += 1
            return ToolResult(content=f"result for {query}", success=True)

        tool._search_tavily = mock_search_tavily
        tool._backend = "tavily"

        with patch.object(tool, '_get_api_key', return_value="fake-key"):
            r1 = tool.run({"query": "test"})
            # Simulate TTL expiry
            tool._cache.clear()
            r2 = tool.run({"query": "test"})

        assert call_count["n"] == 2

    def test_search_different_queries_not_cached(self):
        """Different queries are cached independently."""
        tool = SearchTool()
        call_count = {"n": 0}

        def mock_search_tavily(api_key, query):
            call_count["n"] += 1
            return ToolResult(content=f"result for {query}", success=True)

        tool._search_tavily = mock_search_tavily
        tool._backend = "tavily"

        with patch.object(tool, '_get_api_key', return_value="fake-key"):
            tool.run({"query": "A"})
            tool.run({"query": "B"})

        assert call_count["n"] == 2


class TestLLMRetryBackoff:
    """L3: LLM timeout/429 → exponential backoff retry 1s→2s→4s, 3 retries max."""

    def test_llm_retry_on_error(self):
        """LLMError on first calls → retries → eventually succeeds."""
        from kagent.agents.function_call_agent import FunctionCallAgent
        from kagent.core.config import Config
        from kagent.core.exceptions import LLMError
        from kagent.core.llm import AgentLLM, LLMResponse

        llm = MagicMock(spec=AgentLLM)
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise LLMError("rate limited")
            return LLMResponse(content="answer", usage=None)

        llm.invoke.side_effect = side_effect

        agent = FunctionCallAgent(
            name="test", llm=llm, config=Config(api_key="x"),
        )
        # Patch time.sleep to avoid waiting
        with patch("kagent.agents.function_call_agent.time.sleep"):
            result = agent.run("hi", max_steps=1)

        assert call_count["n"] == 3  # 2 failures + 1 success
        assert result == "answer"

    def test_llm_retry_exhausted(self):
        """All retries fail → LLMError propagates."""
        from kagent.agents.function_call_agent import FunctionCallAgent
        from kagent.core.config import Config
        from kagent.core.exceptions import LLMError
        from kagent.core.llm import AgentLLM

        llm = MagicMock(spec=AgentLLM)
        llm.invoke.side_effect = LLMError("always fails")

        agent = FunctionCallAgent(
            name="test", llm=llm, config=Config(api_key="x"),
        )
        with patch("kagent.agents.function_call_agent.time.sleep"):
            with pytest.raises(LLMError, match="always fails"):
                agent.run("hi", max_steps=1)


class TestMCPAutoReconnect:
    """MCPTool auto-reconnects when subprocess dies."""

    def test_mcp_reconnect_on_broken_pipe(self):
        """BrokenPipeError → reconnect → success on second attempt."""
        from kagent.tools.mcp_tool import MCPTool

        mcp = MCPTool(server_command=["echo", "dummy"], max_reconnects=2)
        connect_count = {"n": 0}

        def mock_connect():
            connect_count["n"] += 1

        def mock_send(method, params):
            if connect_count["n"] <= 1:
                raise BrokenPipeError("pipe closed")
            return {"content": [{"type": "text", "text": "ok"}]}

        mcp.connect = mock_connect
        mcp._send_request = mock_send
        mcp._connected = True
        mcp._cleanup_process = lambda: None

        result = mcp.call_tool("test", {})
        # First attempt: BrokenPipe → cleanup → reconnect → second attempt: success
        assert result.success is True

    def test_mcp_reconnect_exhausted(self):
        """All reconnect attempts fail → error result."""
        from kagent.tools.mcp_tool import MCPTool

        mcp = MCPTool(server_command=["echo", "dummy"], max_reconnects=2)
        mcp._connected = False
        mcp._cleanup_process = lambda: None

        def mock_connect():
            raise ConnectionError("cannot connect")

        mcp.connect = mock_connect

        result = mcp.call_tool("test", {})
        assert result.success is False
        assert "ERROR" in result.content
