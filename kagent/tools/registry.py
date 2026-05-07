"""Tool registry: registration and execution of tools"""

from typing import Any, Callable, Optional

from .base import Tool, ToolResult, ToolParameter


class ToolRegistry:
    """Registry for tools supporting both Tool objects and bare functions"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._functions: dict[str, dict] = {}

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
        """Remove a tool by name. Returns True if removed, False if not found."""
        if name in self._tools:
            del self._tools[name]
            return True
        if name in self._functions:
            del self._functions[name]
            return True
        return False

    def execute_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name with given arguments.

        Returns ToolResult(success=False, ...) for unknown tools or execution errors
        rather than raising exceptions, so Agent loops are never interrupted.
        """
        try:
            # Try tool instances first
            if name in self._tools:
                return self._tools[name].run(arguments)

            # Try registered functions
            if name in self._functions:
                result = self._functions[name]["func"](arguments)
                return ToolResult(content=str(result), success=True)

            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 未注册",
                success=False,
                error="tool_not_found",
            )
        except Exception as e:
            return ToolResult(
                content=f"[ERROR] 工具 '{name}' 执行失败: {e}",
                success=False,
                error=str(e),
            )

    def get_tools_description(self) -> str:
        """Generate a human-readable description of all registered tools."""
        lines = []
        for name, tool in self._tools.items():
            params = tool.get_parameters()
            param_str = ", ".join(
                f"{p.name}: {p.type}"
                + ("?" if not p.required else "")
                + f" — {p.description}"
                for p in params
            )
            lines.append(f"- {name}: {tool.description}\n  参数: {param_str}")

        for name, info in self._functions.items():
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
