"""Subagent harness: run isolated child agent loops from a parent session."""

from __future__ import annotations

import contextvars
import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from app.memory.persistence import PersistenceService
from app.model_client import ModelClient
from app.runtime.host import AgentHost, SubagentHost
from app.runtime.loop import RunCancelledError, run_agent
from app.runtime.messages import AgentResult
from app.runtime.permissions import PermissionPolicy
from app.tools.base import Tool

_log = logging.getLogger(__name__)

# Context variable for the active parent host. Set by the run entrypoint
# (execute_run / _run_cli_turn) so that build_subagent_runner can pick it
# up at call time without capturing it at construction time.
_active_host: contextvars.ContextVar[AgentHost | None] = contextvars.ContextVar(
    "subagent_active_host", default=None,
)


def set_active_host(host: AgentHost | None) -> contextvars.Token:
    """Set the active host for the current async context."""
    return _active_host.set(host)


def reset_active_host(token: contextvars.Token) -> None:
    """Reset the active host after a run completes."""
    _active_host.reset(token)

# Re-exported for convenience; canonical value lives in agent_definitions.
from app.runtime.agent_definitions import DEFAULT_SUBAGENT_MAX_STEPS

SUBAGENT_SYSTEM_PROMPT = (
    "You are a focused subagent. Complete the delegated task described below. "
    "Use available tools when needed. Return a concise final summary when done. "
    "Do not attempt to spawn further subagents."
)


@dataclass
class SubagentResult:
    """Structured result from a subagent run."""

    summary: str
    child_session_id: str
    status: Literal["completed", "max_steps", "error"]
    error: str | None = None
    child_run_id: str = ""
    step_count: int = 0
    message_count: int = 0


def generate_child_session_id(parent_session_id: str) -> str:
    """Generate a distinct child session id that fits the 80-char limit."""
    parent_hash = hashlib.sha256(parent_session_id.encode()).hexdigest()[:12]
    short = uuid.uuid4().hex[:8]
    return f"sub_{parent_hash}_{short}"


async def run_subagent(
    *,
    prompt: str,
    parent_session_id: str,
    model_client: ModelClient,
    build_child_tools: Callable[[str], list[Tool]],
    policy: PermissionPolicy | None = None,
    project_root: Path,
    persistence: PersistenceService | None = None,
    max_steps: int = DEFAULT_SUBAGENT_MAX_STEPS,
    host: AgentHost | None = None,
    system_prompt: str = SUBAGENT_SYSTEM_PROMPT,
) -> SubagentResult:
    """Run an isolated child agent loop for the given prompt.

    ``build_child_tools`` is called with the child session id so that
    tools like TodoWriteTool bind to the child session rather than the parent.

    The child starts with fresh messages (no parent transcript) and uses
    the filtered tool list provided. Returns a SubagentResult with the
    child's final summary or error details.
    """
    child_session_id = generate_child_session_id(parent_session_id)
    child_tools = build_child_tools(child_session_id)
    raw_host = host or _active_host.get()
    # Wrap the parent host so child events don't leak into the parent
    # RunManager (which doesn't know the child's run_id).  Permission
    # requests are re-written with the parent's identifiers and forwarded.
    if raw_host is not None and hasattr(raw_host, "run_id") and hasattr(raw_host, "session_id"):
        effective_host: AgentHost | None = SubagentHost(
            parent_host=raw_host,
            parent_run_id=raw_host.run_id,
            parent_session_id=raw_host.session_id,
        )
    else:
        effective_host = raw_host
    _log.info(
        "subagent starting: child=%s parent=%s max_steps=%d",
        child_session_id, parent_session_id, max_steps,
    )

    try:
        result: AgentResult = await run_agent(
            user_input=prompt,
            model_client=model_client,
            tools=child_tools,
            max_steps=max_steps,
            session_id=child_session_id,
            policy=policy,
            project_root=project_root,
            persistence=persistence,
            system_prompt=system_prompt,
            host=effective_host,
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "max steps" in msg.lower():
            _log.warning("subagent hit max steps: child=%s", child_session_id)
            return SubagentResult(
                summary=f"Subagent stopped: {msg}",
                child_session_id=child_session_id,
                status="max_steps",
                error=msg,
            )
        _log.error("subagent runtime error: child=%s error=%s", child_session_id, msg)
        return SubagentResult(
            summary=f"Subagent failed: {msg}",
            child_session_id=child_session_id,
            status="error",
            error=msg,
        )
    except RunCancelledError:
        raise
    except Exception as exc:
        msg = str(exc)
        _log.error("subagent unexpected error: child=%s error=%s", child_session_id, msg)
        return SubagentResult(
            summary=f"Subagent failed: {msg}",
            child_session_id=child_session_id,
            status="error",
            error=msg,
        )

    _log.info(
        "subagent completed: child=%s steps=%d messages=%d",
        child_session_id, len(result.steps), result.message_count,
    )
    return SubagentResult(
        summary=result.answer or "(subagent completed with no text output)",
        child_session_id=child_session_id,
        status="completed",
        child_run_id=result.steps[-1].tool_use_id if result.steps else "",
        step_count=len(result.steps),
        message_count=result.message_count,
    )
