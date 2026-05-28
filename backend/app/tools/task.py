"""Subagent task tool: delegates a bounded prompt to an isolated child agent."""

from __future__ import annotations

from typing import Any, Callable, Coroutine

# Default conservative step limit for child agents (duplicated from subagent.py
# to avoid circular import: task -> subagent -> loop -> registry -> task).
DEFAULT_SUBAGENT_MAX_STEPS = 5

TOOL_NAME = "task"
TOOL_DESCRIPTION = (
    "Delegate a bounded task to an isolated subagent. The subagent runs with "
    "fresh context and returns a concise summary when finished. Use this for "
    "exploratory research, multi-step file analysis, or focused implementation "
    "tasks that would pollute the main conversation context.\n\n"
    "The prompt must be self-contained: include all context the subagent needs "
    "since it does not see the parent conversation history."
)


class TaskTool:
    """Parent-facing tool that dispatches work to a subagent.

    The runner callable should accept ``prompt`` and optional ``max_steps``
    keyword arguments and return an object with ``summary``, ``status``,
    and ``error`` attributes (i.e. a SubagentResult).
    """

    name = TOOL_NAME
    description = TOOL_DESCRIPTION
    risk_level: str = "medium"
    input_schema: dict[str, Any] = {
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

    def __init__(self, runner: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        self._runner = runner

    async def call(self, input: dict[str, Any]) -> str:
        prompt = input.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("task requires a non-empty 'prompt' string")

        max_steps = input.get("max_steps")
        if max_steps is not None:
            max_steps = int(max_steps)
            max_steps = max(1, min(max_steps, 16))

        result = await self._runner(prompt=prompt, max_steps=max_steps)
        return _format_result(result)


def _format_result(result: Any) -> str:
    """Format a SubagentResult as a concise tool result string."""
    if result.status == "completed":
        return result.summary
    if result.status == "max_steps":
        return f"[Subagent stopped: reached maximum steps]\n{result.summary}"
    return f"[Subagent error: {result.error or 'unknown'}]\n{result.summary}"
