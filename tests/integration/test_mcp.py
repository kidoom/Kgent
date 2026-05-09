"""D4-D6 integration tests: MCPTool + MCP Server + ToolRegistry.register_mcp"""

import sys
import os
import pytest

from kagent.tools.mcp_tool import MCPTool
from kagent.tools.registry import ToolRegistry


def _server_command():
    """Get the command to start the MCP template server."""
    return [sys.executable, "-m", "kagent.tools.mcp_server_template"]


class TestMCPTool:
    def test_mcp_connect_and_discover(self):
        """Connect to MCP server and discover tools."""
        mcp = MCPTool(server_command=_server_command())
        try:
            tools = mcp.discover_tools()
            assert len(tools) == 2
            names = {t.name for t in tools}
            assert "search_docs" in names
            assert "list_sources" in names

            # Check tool parameters
            search_tool = next(t for t in tools if t.name == "search_docs")
            params = search_tool.get_parameters()
            assert len(params) == 1
            assert params[0].name == "query"
            assert params[0].required is True
        finally:
            mcp.close()

    def test_mcp_call_tool(self):
        """Call a remote tool and get a valid result."""
        mcp = MCPTool(server_command=_server_command())
        try:
            mcp.connect()
            result = mcp.call_tool("list_sources", {})
            assert result.success is True
            assert "文档来源" in result.content or "Kagent" in result.content
        finally:
            mcp.close()

    def test_mcp_call_search_docs(self):
        """Search for documents via MCP."""
        mcp = MCPTool(server_command=_server_command())
        try:
            mcp.connect()
            result = mcp.call_tool("search_docs", {"query": "MCP"})
            assert result.success is True
            assert "MCP" in result.content
        finally:
            mcp.close()

    def test_mcp_call_unknown_tool(self):
        """Calling an unknown tool returns error result."""
        mcp = MCPTool(server_command=_server_command())
        try:
            mcp.connect()
            result = mcp.call_tool("nonexistent_tool", {})
            # MCP server returns isError=True for unknown tools
            assert result.success is False
        finally:
            mcp.close()

    def test_mcp_close_and_reconnect(self):
        """After close(), calling a tool triggers auto-reconnect."""
        mcp = MCPTool(server_command=_server_command(), max_reconnects=2)
        try:
            mcp.connect()
            result1 = mcp.call_tool("list_sources", {})
            assert result1.success is True

            # Force close the connection
            mcp._connected = False
            mcp._cleanup_process()

            # Should auto-reconnect
            result2 = mcp.call_tool("list_sources", {})
            assert result2.success is True
        finally:
            mcp.close()


class TestMCPToolRegistryIntegration:
    def test_register_mcp(self):
        """register_mcp auto-discovers and registers remote tools."""
        mcp = MCPTool(server_command=_server_command())
        registry = ToolRegistry()
        try:
            registered = registry.register_mcp(mcp)
            assert len(registered) == 2
            assert "search_docs" in registered
            assert "list_sources" in registered

            # Tools should be executable via registry
            result = registry.execute_tool("list_sources", {})
            assert result.success is True
        finally:
            mcp.close()

    def test_mcp_tools_in_description(self):
        """MCP tools appear in get_tools_description()."""
        mcp = MCPTool(server_command=_server_command())
        registry = ToolRegistry()
        try:
            registry.register_mcp(mcp)
            desc = registry.get_tools_description()
            assert "search_docs" in desc
            assert "list_sources" in desc
        finally:
            mcp.close()

    def test_unregister_mcp_tool(self):
        """Unregister a single MCP tool from the registry."""
        mcp = MCPTool(server_command=_server_command())
        registry = ToolRegistry()
        try:
            registry.register_mcp(mcp)
            assert registry.is_registered("search_docs")

            registry.unregister("search_docs")
            assert not registry.is_registered("search_docs")

            # list_sources should still be registered
            assert registry.is_registered("list_sources")
        finally:
            mcp.close()
