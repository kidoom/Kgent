"""In-process short-term session memory (V0.1.1)."""

from app.agent.messages import Message
from app.agent.prompts import SYSTEM_PROMPT

SESSIONS: dict[str, list[Message]] = {}


def get_or_create_session(session_id: str) -> list[Message]:
    return SESSIONS.setdefault(
        session_id,
        [Message(role="system", content=SYSTEM_PROMPT)],
    )


def trim_session_messages(messages: list[Message], max_messages: int) -> None:
    """Keep the system prompt and the most recent tail of the session."""
    if max_messages < 2:
        max_messages = 2
    if len(messages) <= max_messages:
        return
    if messages and messages[0].role == "system":
        messages[:] = [messages[0], *messages[-(max_messages - 1) :]]
        return
    messages[:] = messages[-max_messages:]


def reset_sessions() -> None:
    """Clear all sessions. Intended for tests."""
    SESSIONS.clear()
