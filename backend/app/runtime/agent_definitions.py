"""Agent definitions for named subagent roles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

# Default max steps shared across all definitions.
DEFAULT_SUBAGENT_MAX_STEPS = 5

# Shared final-answer delivery format for subagent payload parsing.
FINAL_ANSWER_DELIVERY_FORMAT = (
    "\n\nWhen you are done, deliver your final answer using the following "
    "Markdown sections (use only the sections that apply):\n\n"
    "## Summary\n"
    "A concise overview of what you found or did.\n\n"
    "## Findings\n"
    "- Key observations, evidence, or analysis results.\n\n"
    "## Files\n"
    "- Files you inspected or modified.\n\n"
    "## Actions\n"
    "- Concrete steps you took or changes you made.\n\n"
    "## Risks\n"
    "- Potential issues, caveats, or concerns.\n\n"
    "## Next steps\n"
    "- Recommended follow-up actions."
)


@dataclass(frozen=True)
class AgentDefinition:
    """Configuration for a named subagent type."""

    name: str
    description: str
    system_prompt: str
    default_max_steps: int = DEFAULT_SUBAGENT_MAX_STEPS
    allowed_tools: tuple[str, ...] | None = None  # None = no restriction
    disallowed_tools: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Built-in system prompts
# ---------------------------------------------------------------------------

_GENERAL_PURPOSE_PROMPT = (
    "You are a focused subagent. Complete the delegated task described below. "
    "Use available tools when needed. Return a concise final summary when done. "
    "Do not attempt to spawn further subagents."
)

_RESEARCHER_PROMPT = (
    "You are a read-only research subagent. Investigate the codebase, read files, "
    "search for patterns, and gather information. Do NOT modify any files or "
    "execute commands that change system state. Return a concise summary of "
    "your findings. Do not attempt to spawn further subagents."
)

_IMPLEMENTER_PROMPT = (
    "You are an implementation subagent. Make the code changes described in the "
    "task. Use edit/write tools as needed. Keep changes minimal and focused. "
    "Return a concise summary of what you changed. "
    "Do not attempt to spawn further subagents."
)

_REVIEWER_PROMPT = (
    "You are a read-only review subagent. Review code for correctness, risks, "
    "missing tests, and style issues. Do NOT modify any files. "
    "Return a concise summary of your findings and recommendations. "
    "Do not attempt to spawn further subagents."
)

# ---------------------------------------------------------------------------
# Built-in definitions
# ---------------------------------------------------------------------------

GENERAL_PURPOSE = AgentDefinition(
    name="general-purpose",
    description="Broad multi-step work using all available tools.",
    system_prompt=_GENERAL_PURPOSE_PROMPT + FINAL_ANSWER_DELIVERY_FORMAT,
)

RESEARCHER = AgentDefinition(
    name="researcher",
    description="Read-only code and project investigation.",
    system_prompt=_RESEARCHER_PROMPT + FINAL_ANSWER_DELIVERY_FORMAT,
    allowed_tools=(
        "calculator", "list_files", "read_file", "grep",
        "web_fetch", "git_status", "git_diff", "git_log",
    ),
)

IMPLEMENTER = AgentDefinition(
    name="implementer",
    description="Focused implementation tasks with edit/write tools.",
    system_prompt=_IMPLEMENTER_PROMPT + FINAL_ANSWER_DELIVERY_FORMAT,
)

REVIEWER = AgentDefinition(
    name="reviewer",
    description="Read-only review of changes, risks, and missing tests.",
    system_prompt=_REVIEWER_PROMPT + FINAL_ANSWER_DELIVERY_FORMAT,
    allowed_tools=(
        "calculator", "list_files", "read_file", "grep",
        "web_fetch", "git_status", "git_diff", "git_log",
    ),
)

_BUILTIN_DEFINITIONS: tuple[AgentDefinition, ...] = (
    GENERAL_PURPOSE,
    RESEARCHER,
    IMPLEMENTER,
    REVIEWER,
)


class AgentRegistry:
    """Registry that resolves agent_type names to AgentDefinition objects."""

    def __init__(self, definitions: Sequence[AgentDefinition] = ()) -> None:
        self._defs: dict[str, AgentDefinition] = {}
        for d in (definitions or _BUILTIN_DEFINITIONS):
            self._defs[d.name] = d

    def get(self, agent_type: str) -> AgentDefinition:
        """Return the definition for *agent_type*, or raise KeyError."""
        try:
            return self._defs[agent_type]
        except KeyError:
            available = ", ".join(sorted(self._defs))
            raise KeyError(
                f"Unknown agent type '{agent_type}'. "
                f"Available agent types: {available}"
            ) from None

    def available_types(self) -> list[str]:
        return sorted(self._defs)


# Module-level default registry.
_default_registry: AgentRegistry | None = None


def get_default_registry() -> AgentRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry


_UNIVERSAL_DENY: set[str] = {"task"}


def filter_tools_for_definition(
    tools: list,
    definition: AgentDefinition,
) -> list:
    """Return *tools* filtered according to the definition's allow/deny lists.

    - ``task`` is always removed (subagents must not recurse).
    - If ``allowed_tools`` is set, only tools whose ``name`` appears in it are kept.
    - Tools whose ``name`` appears in ``disallowed_tools`` are always removed.
    - ``disallowed_tools`` takes precedence over ``allowed_tools``.
    """
    deny = _UNIVERSAL_DENY | set(definition.disallowed_tools)
    result = []
    for tool in tools:
        name = tool.name
        if name in deny:
            continue
        if definition.allowed_tools is not None and name not in definition.allowed_tools:
            continue
        result.append(tool)
    return result
