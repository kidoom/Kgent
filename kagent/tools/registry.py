"""Tool registry: registration, lifecycle, and execution of tools"""

import threading
from typing import Any, Callable, Optional, TYPE_CHECKING

from .base import Tool, ToolResult, ToolParameter

if TYPE_CHECKING:
    from .mcp_tool import MCPTool


class ToolRegistry:
    """Pluggable tool registry — register, disable, execute, unregister.

    Supports two registration modes:
      - Tool objects: register_tool(tool)
      - Bare functions: register_function(name, desc, func)

    Lifecycle: register → [disable ⇄ enable] → execute → unregister
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict] = {}
        self._disabled: set[str] = set()
        self._lock = threading.Lock()

    # ── Registration ──────────────────────────────────────────

    def register_tool(self, tool: Tool) -> None:
        """Register a Tool instance."""
        if not isinstance(tool, Tool):
            raise TypeError(f"Expected Tool instance, got {type(tool).__name__}")
        with self._lock:
            self._tools[tool.name] = tool

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable[[dict], Any],
        parameters: Optional[list[ToolParameter]] = None,
    ) -> None:
        """Register a bare function as a tool."""
        with self._lock:
            self._functions[name] = {
                "name": name,
                "description": description,
                "func": func,
                "parameters": parameters or [],
            }

    def register_mcp(self, mcp_tool: "MCPTool") -> list[str]:
        """Auto-discover and register all tools from an MCPTool.

        Returns the list of registered tool names.
        """
        remote_tools = mcp_tool.discover_tools()
        registered = []
        for tool in remote_tools:
            self.register_tool(tool)
            registered.append(tool.name)
        return registered

    def unregister(self, name: str) -> bool:
        """Permanently remove a tool. Returns True if removed."""
        with self._lock:
            self._disabled.discard(name)
            if name in self._tools:
                del self._tools[name]
                return True
            if name in self._functions:
                del self._functions[name]
                return True
            return False

    # ── Lifecycle ─────────────────────────────────────────────

    def disable(self, name: str) -> bool:
        """Disable a registered tool. Disabled tools reject execution."""
        with self._lock:
            if name in self._tools or name in self._functions:
                self._disabled.add(name)
                return True
            return False

    def enable(self, name: str) -> bool:
        """Re-enable a previously disabled tool."""
        with self._lock:
            if name in self._disabled:
                self._disabled.discard(name)
                return True
            return False

    def is_enabled(self, name: str) -> bool:
        """Check if a tool is currently enabled for execution."""
        if name not in self._tools and name not in self._functions:
            return False
        return name not in self._disabled

    def is_registered(self, name: str) -> bool:
        """Check if a tool name is registered (regardless of disabled state)."""
        return name in self._tools or name in self._functions

    # ── Execution ─────────────────────────────────────────────

    def execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name. Always returns ToolResult — never raises.

        Guards:
          1. Not registered → error
          2. Disabled → rejected
          3. Execution error → ToolResult(success=False)
        """
        # Take an immutable snapshot of the registry state under lock
        with self._lock:
            tool = self._tools.get(name)
            func_info = self._functions.get(name)
            is_disabled = name in self._disabled
            is_known = tool is not None or func_info is not None

        # Guard: not registered
        if not is_known:
            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 未注册",
                success=False,
                error="tool_not_found",
            )
        # Guard: disabled
        if is_disabled:
            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 已被禁用",
                success=False,
                error="tool_disabled",
            )

        try:
            if tool is not None:
                return tool.run(arguments)

            if func_info is not None:
                result = func_info["func"](arguments)
                return ToolResult(content=str(result), success=True)
        except Exception as e:
            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 执行失败: {e}",
                success=False,
                error=str(e),
            )

        return ToolResult(
            content=f"[ERROR] 工具 '{name}' 未注册",
            success=False,
            error="tool_not_found",
        )

    # ── Introspection ─────────────────────────────────────────

    def list_tools(self) -> dict[str, dict]:
        """Return all registered tools with status: {name: {type, description, enabled}}"""
        result = {}
        for name, tool in self._tools.items():
            result[name] = {
                "type": "tool",
                "description": tool.description,
                "enabled": name not in self._disabled,
            }
        for name, info in self._functions.items():
            result[name] = {
                "type": "function",
                "description": info["description"],
                "enabled": name not in self._disabled,
            }
        return result

    def get_tools_description(self) -> str:
        """Human-readable description of enabled tools (for prompts)."""
        lines = []
        for name, tool in self._tools.items():
            if name in self._disabled:
                continue
            params = tool.get_parameters()
            param_str = ", ".join(
                f"{p.name}: {p.type}"
                + ("?" if not p.required else "")
                + f" — {p.description}"
                for p in params
            )
            lines.append(f"- {name}: {tool.description}\n  参数: {param_str}")

        for name, info in self._functions.items():
            if name in self._disabled:
                continue
            params = info.get("parameters", [])
            if params:
                param_str = ", ".join(
                    f"{p.name}: {p.type}"
                    + ("?" if not p.required else "")
                    + f" — {p.description}"
                    for p in params
                )
            else:
                param_str = "无参数"
            lines.append(f"- {name}: {info['description']}\n  参数: {param_str}")

        return "\n".join(lines) if lines else "(无可用工具)"
