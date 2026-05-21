"""Tool protocol and schema projection."""

from typing import Any, Literal, Protocol

RiskLevel = Literal["low", "medium", "high"]


class Tool(Protocol):
    name: str
    description: str
    input_schema: dict[str, Any]
    risk_level: RiskLevel

    async def call(self, input: dict[str, Any]) -> str:
        """Execute this tool with validated JSON-like input."""
        ...


def tool_to_schema(tool: Tool) -> dict[str, Any]:
    """Return the thin schema view that is safe to send to the model.

    `risk_level` is intentionally NOT projected: it is runtime-only metadata
    used by the permission policy, not by the model.
    """

    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }
