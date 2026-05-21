from app.runtime.messages import Message
from app.memory.session_store import get_or_create_session, reset_sessions, trim_session_messages


def test_trim_session_keeps_system_and_tail() -> None:
    reset_sessions()
    messages = get_or_create_session("trim-test")
    for index in range(20):
        messages.append(Message(role="user", content=f"message-{index}"))

    trim_session_messages(messages, max_messages=6)

    assert len(messages) == 6
    assert messages[0].role == "system"
    assert messages[-1].content == "message-19"
    assert messages[1].content == "message-15"
