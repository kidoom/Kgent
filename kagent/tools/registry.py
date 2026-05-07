"""Tool registry: registration, lifecycle, and execution of tools"""

from typing import Any, Callable, Optional

from .base import Tool, ToolResult, ToolParameter


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

    # ── Registration ──────────────────────────────────────────

    def register_tool(self, tool: Tool) -> None:
        """Register a Tool instance."""
        if not isinstance(tool, Tool):
            raise TypeError(f"Expected Tool instance, got {type(tool).__name__}")
        self._tools[tool.name] = tool

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable[[dict], Any],
        parameters: Optional[list[ToolParameter]] = None,
    ) -> None:
        """Register a bare function as a tool."""
        self._functions[name] = {
            "name": name,
            "description": description,
            "func": func,
            "parameters": parameters or [],
        }

    def unregister(self, name: str) -> bool:
        """Permanently remove a tool. Returns True if removed."""
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
        if name in self._tools or name in self._functions:
            self._disabled.add(name)
            return True
        return False

    def enable(self, name: str) -> bool:
        """Re-enable a previously disabled tool."""
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
        # Guard: not registered
        if not self.is_registered(name):
            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 未注册",
                success=False,
                error="tool_not_found",
            )
        # Guard: disabled
        if not self.is_enabled(name):
            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 已被禁用",
                success=False,
                error="tool_disabled",
            )

        try:
            if name in self._tools:
                return self._tools[name].run(arguments)

            if name in self._functions:
                result = self._functions[name]["func"](arguments)
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
