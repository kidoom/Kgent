"""Tool permission policies (V0.2).

`risk_level` is metadata carried by the tool itself. A `PermissionPolicy`
decides what to do at runtime when the model emits a tool_use:

    allow -> tool runs normally
    deny  -> tool is short-circuited, a synthetic permission_denied
             tool_result(is_error=True) is fed back to the model so the
             loop continues without crashing (spec section 12)
    ask   -> CLI asker is invoked. On the API side the orchestrator
             must downgrade interactive to risk_based to avoid HTTP
             long-blocking.

The policy never executes the tool itself. It only returns a decision.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal, Protocol

from pydantic import BaseModel

from app.runtime.messages import ToolUseBlock
from app.tools.base import Tool

PermissionAction = Literal["allow", "deny", "ask"]
PermissionMode = Literal["allow_all", "risk_based", "interactive"]

DEFAULT_RISK_BASED_ALLOWED: tuple[str, ...] = ("low", "medium")


class PermissionDecision(BaseModel):
    """The outcome of `PermissionPolicy.decide`."""

    action: PermissionAction
    reason: str = ""


class PermissionPolicy(Protocol):
    name: str

    async def decide(self, tool: Tool, tool_use: ToolUseBlock) -> PermissionDecision:
        """Inspect a tool_use and return whether it may execute."""
        ...


class AllowAllPolicy:
    """Allow every tool_use. Same behaviour as Kgent up to V0.1.4."""

    name = "allow_all"

    async def decide(self, tool: Tool, tool_use: ToolUseBlock) -> PermissionDecision:
        return PermissionDecision(action="allow", reason="allow_all policy")


class RiskBasedPolicy:
    """Allow tools whose `risk_level` is in `allowed`; deny the rest."""

    name = "risk_based"

    def __init__(self, allowed: tuple[str, ...] = DEFAULT_RISK_BASED_ALLOWED):
        self._allowed = tuple(allowed)

    async def decide(self, tool: Tool, tool_use: ToolUseBlock) -> PermissionDecision:
        risk = getattr(tool, "risk_level", "high")
        if risk in self._allowed:
            return PermissionDecision(
                action="allow",
                reason=f"risk_level={risk} in {self._allowed}",
            )
        return PermissionDecision(
            action="deny",
            reason=f"risk_level={risk} not in {self._allowed}",
        )


# An asker takes (tool, tool_use) and returns True (approve) / False (reject).
PermissionAsker = Callable[[Tool, ToolUseBlock], Awaitable[bool]]


class InteractivePolicy:
    """Allow `low`; for `medium`/`high` defer to an async `asker`.

    Legacy V0.2 policy — prefer AskPolicy + AgentHost for V0.2.1+.
    """

    name = "interactive"

    def __init__(self, asker: PermissionAsker):
        self._asker = asker

    async def decide(self, tool: Tool, tool_use: ToolUseBlock) -> PermissionDecision:
        risk = getattr(tool, "risk_level", "high")
        if risk == "low":
            return PermissionDecision(action="allow", reason="low-risk auto-approved")
        approved = await self._asker(tool, tool_use)
        if approved:
            return PermissionDecision(action="allow", reason="user approved")
        return PermissionDecision(action="deny", reason="user rejected")


class AskPolicy:
    """Allow `low`; for `medium`/`high` return `ask` for AgentHost to resolve."""

    name = "ask"

    async def decide(self, tool: Tool, tool_use: ToolUseBlock) -> PermissionDecision:
        risk = getattr(tool, "risk_level", "high")
        if risk == "low":
            return PermissionDecision(action="allow", reason="low-risk auto-approved")
        return PermissionDecision(
            action="ask",
            reason=f"risk_level={risk} requires user approval",
        )


def normalize_mode(raw: str | None) -> PermissionMode:
    """Normalize a free-form mode string. Invalid values fall back to `risk_based`."""
    if not raw:
        return "risk_based"
    candidate = raw.strip().lower().replace("-", "_")
    if candidate in {"allow_all", "risk_based", "interactive"}:
        return candidate  # type: ignore[return-value]
    return "risk_based"


def build_policy(
    mode: PermissionMode,
    *,
    asker: PermissionAsker | None = None,
) -> PermissionPolicy:
    """Construct a policy for a given mode.

    For `interactive`, an `asker` callable must be supplied. Callers without
    a usable asker (e.g. the API route) should downgrade to `risk_based`
    BEFORE calling this and indicate the downgrade in observability.
    """
    if mode == "allow_all":
        return AllowAllPolicy()
    if mode == "interactive":
        if asker is None:
            raise ValueError("InteractivePolicy requires an asker callable")
        return InteractivePolicy(asker=asker)
    return RiskBasedPolicy()
