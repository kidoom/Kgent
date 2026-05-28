"""In-process short-term session memory (V0.1.1)."""

from __future__ import annotations

from collections.abc import Callable

from app.runtime.context_compression import trim_session_messages_safely
from app.runtime.messages import Message

SESSIONS: dict[str, list[Message]] = {}


def get_or_create_session(
    session_id: str,
    *,
    hydrate_fn: Callable[[str], list[Message]] | None = None,
) -> list[Message]:
    # Session history stores only real user/assistant/tool observation messages.
    # Context is injected just-in-time by runtime.context_builder.
    if session_id not in SESSIONS and hydrate_fn is not None:
        SESSIONS[session_id] = hydrate_fn(session_id)
    return SESSIONS.setdefault(session_id, [])


def has_session(session_id: str) -> bool:
    return session_id in SESSIONS


def delete_session(session_id: str) -> bool:
    return SESSIONS.pop(session_id, None) is not None


def trim_session_messages(messages: list[Message], max_messages: int) -> None:
    """Keep the most recent messages while preserving tool_use/tool_result pairs."""
    trim_session_messages_safely(messages, max_messages)


def reset_sessions() -> None:
    """Clear all sessions. Intended for tests."""
    SESSIONS.clear()
