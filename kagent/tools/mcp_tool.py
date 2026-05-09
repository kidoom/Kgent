"""MCPTool — MCP protocol client over stdio (subprocess + JSON-RPC 2.0)"""

import json
import subprocess
import threading
from typing import Any, Optional

from ..core.exceptions import ToolError
from .base import Tool, ToolResult, ToolParameter


class MCPTool:
    """MCP (Model Context Protocol) client.

    Spawns an MCP server as a subprocess and communicates via JSON-RPC 2.0
    over stdin/stdout. Supports:
      - initialize + tools/list for tool discovery
      - tools/call for tool invocation
      - Automatic reconnection (up to max_reconnects)
    """

    def __init__(
        self,
        server_command: list[str],
        max_reconnects: int = 3,
        timeout: float = 30.0,
    ):
        self._command = server_command
        self._max_reconnects = max_reconnects
        self._timeout = timeout
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._tools_cache: list[dict] = []
        self._connected = False

    # ── Public API ──────────────────────────────────────────────

    def connect(self) -> None:
        """Start the MCP server subprocess and initialize the protocol."""
        self._start_process()
        self._initialize()

    def discover_tools(self) -> list[Tool]:
        """Call tools/list and return Tool wrappers for each remote tool."""
        if not self._connected:
            self.connect()

        result = self._send_request("tools/list", {})
        self._tools_cache = result.get("tools", [])

        tools = []
        for t in self._tools_cache:
            tools.append(MCPRemoteTool(
                name=t["name"],
                description=t.get("description", ""),
                parameters_schema=t.get("inputSchema", {}),
                mcp_tool=self,
            ))
        return tools

    def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Call a remote tool via tools/call. Reconnects on failure."""
        for attempt in range(self._max_reconnects + 1):
            try:
                if not self._connected:
                    self.connect()
                result = self._send_request("tools/call", {
                    "name": name,
                    "arguments": arguments,
                })
                # MCP result format: {content: [{type, text}, ...]}
                content_parts = result.get("content", [])
                text_parts = [
                    p.get("text", "") for p in content_parts if p.get("type") == "text"
                ]
                content = "\n".join(text_parts) if text_parts else json.dumps(result)
                is_error = result.get("isError", False)
                return ToolResult(
                    content=content,
                    success=not is_error,
                    error="mcp_error" if is_error else None,
                )
            except (BrokenPipeError, ConnectionError, OSError) as e:
                self._connected = False
                self._cleanup_process()
                if attempt < self._max_reconnects:
                    continue
                return ToolResult(
                    content=f"[ERROR] MCP tool '{name}' 调用失败: {e}",
                    success=False,
                    error=str(e),
                )
            except Exception as e:
                return ToolResult(
                    content=f"[ERROR] MCP tool '{name}' 调用失败: {e}",
                    success=False,
                    error=str(e),
                )

    def close(self) -> None:
        """Clean up the subprocess."""
        self._connected = False
        self._cleanup_process()

    # ── Internal ────────────────────────────────────────────────

    def _start_process(self) -> None:
        """Start the MCP server subprocess."""
        try:
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise ToolError(
                user_message=f"MCP Server 启动失败: 找不到命令 '{self._command[0]}'",
                debug_message=f"command={self._command}, error={e}",
            ) from e
        except Exception as e:
            raise ToolError(
                user_message=f"MCP Server 启动失败: {e}",
                debug_message=f"command={self._command}, error={type(e).__name__}: {e}",
            ) from e

    def _initialize(self) -> None:
        """Send MCP initialize request and wait for response."""
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "kagent", "version": "0.3.0"},
        })
        # Send initialized notification
        self._send_notification("notifications/initialized", {})
        self._connected = True

    def _next_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _send_request(self, method: str, params: dict) -> dict:
        """Send a JSON-RPC request and wait for the response."""
        if not self._process or self._process.poll() is not None:
            raise ConnectionError("MCP server process is not running")

        req_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        payload = json.dumps(request) + "\n"

        with self._lock:
            self._process.stdin.write(payload.encode())
            self._process.stdin.flush()

            # Read response line
            line = self._process.stdout.readline()
            if not line:
                raise ConnectionError("MCP server closed stdout")

            response = json.loads(line.decode())

        if "error" in response:
            err = response["error"]
            raise ToolError(
                user_message=f"MCP 请求失败: {err.get('message', 'unknown')}",
                debug_message=f"method={method}, error={err}",
            )

        return response.get("result", {})

    def _send_notification(self, method: str, params: dict) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._process or self._process.poll() is not None:
            return
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        payload = json.dumps(notification) + "\n"
        with self._lock:
            self._process.stdin.write(payload.encode())
            self._process.stdin.flush()

    def _cleanup_process(self) -> None:
        """Terminate the subprocess if still running."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None


class MCPRemoteTool(Tool):
    """A Tool wrapper that delegates execution to a remote MCP server tool."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict,
        mcp_tool: MCPTool,
    ):
        super().__init__(name=name, description=description)
        self._schema = parameters_schema
        self._mcp = mcp_tool

    def run(self, parameters: dict) -> ToolResult:
        return self._mcp.call_tool(self.name, parameters)

    def get_parameters(self) -> list[ToolParameter]:
        """Convert MCP inputSchema to ToolParameter list."""
        params = []
        properties = self._schema.get("properties", {})
        required_set = set(self._schema.get("required", []))
        for prop_name, prop_def in properties.items():
            params.append(ToolParameter(
                name=prop_name,
                type=prop_def.get("type", "string"),
                description=prop_def.get("description", ""),
                required=prop_name in required_set,
            ))
        return params
