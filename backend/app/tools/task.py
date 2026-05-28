"""Subagent task tool: delegates a bounded prompt to an isolated child agent."""

from __future__ import annotations

from typing import Any, Callable, Coroutine, Sequence

from app.runtime.agent_definitions import DEFAULT_SUBAGENT_MAX_STEPS

TOOL_NAME = "task"


def _build_description(roles: Sequence[str]) -> str:
    role_list = ", ".join(roles)
    return (
        "Delegate a bounded task to an isolated subagent. The subagent runs with "
        "fresh context and returns a concise summary when finished. Use this for "
        "exploratory research, multi-step file analysis, or focused implementation "
        "tasks that would pollute the main conversation context.\n\n"
        "The prompt must be self-contained: include all context the subagent needs "
        "since it does not see the parent conversation history.\n\n"
        f"Available agent_type roles: {role_list}."
    )


def _build_input_schema(agent_types: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Self-contained task description for the subagent. "
                    "Include all necessary context since the subagent has no "
                    "access to the parent conversation."
                ),
            },
            "agent_type": {
                "type": "string",
                "enum": list(agent_types),
                "description": (
                    f"Subagent role (default: {agent_types[0]})."
                ),
            },
            "max_steps": {
                "type": "integer",
                "description": (
                    f"Maximum agent steps the subagent may take (default: {DEFAULT_SUBAGENT_MAX_STEPS})."
                ),
            },
        },
        "required": ["prompt"],
        "additionalProperties": False,
    }


class TaskTool:
    """Parent-facing tool that dispatches work to a subagent.

    The runner callable should accept ``prompt``, ``agent_type``, and optional
    ``max_steps`` keyword arguments and return an object with ``summary``,
    ``status``, and ``error`` attributes (i.e. a SubagentResult).
    """

    risk_level: str = "medium"

    def __init__(
        self,
        runner: Callable[..., Coroutine[Any, Any, Any]],
        agent_types: Sequence[str] = ("general-purpose", "researcher", "implementer", "reviewer"),
    ) -> None:
        self._runner = runner
        self.name = TOOL_NAME
        self.input_schema = _build_input_schema(agent_types)
        self.description = _build_description(agent_types)

    async def call(self, input: dict[str, Any]) -> str:
        prompt = input.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("task requires a non-empty 'prompt' string")

        allowed = set(self.input_schema["properties"]["agent_type"]["enum"])
        agent_type = input.get("agent_type") or "general-purpose"
        if agent_type not in allowed:
            available = ", ".join(sorted(allowed))
            return _format_error(
                f"Unknown agent type '{agent_type}'. Available agent types: {available}"
            )

        max_steps = input.get("max_steps")
        if max_steps is not None:
            max_steps = int(max_steps)
            max_steps = max(1, min(max_steps, 16))

        result = await self._runner(prompt=prompt, agent_type=agent_type, max_steps=max_steps)
        return _format_result(result)


def _format_error(message: str) -> str:
    return f"[Subagent error: {message}]"


def _format_result(result: Any) -> str:
    """Format a SubagentResult as a concise tool result string."""
    if result.status == "completed":
        return result.summary
    if result.status == "max_steps":
        return f"[Subagent stopped: reached maximum steps]\n{result.summary}"
    return f"[Subagent error: {result.error or 'unknown'}]\n{result.summary}"
