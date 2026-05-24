from pathlib import Path

from app.runtime.context_builder import build_context_bundle, build_model_messages
from app.runtime.messages import Message, ToolResultBlock, ToolUseBlock


def _joined(messages: list[Message]) -> str:
    parts: list[str] = []
    for message in messages:
        if isinstance(message.content, str):
            parts.append(message.content)
    return "\n".join(parts)


def test_build_model_messages_adds_system_and_user_context(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("Follow project instructions.", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n\nA tiny project.", encoding="utf-8")
    session = [Message(role="user", content="What is this project?")]

    messages = build_model_messages(session, project_root=tmp_path)

    assert messages[0].role == "system"
    assert isinstance(messages[0].content, str)
    assert "projectRoot:" in messages[0].content
    assert "runtime:" in messages[0].content
    assert "fileSafety:" in messages[0].content
    assert messages[1].is_meta is True
    assert "<project-instructions>" in str(messages[1].content)
    assert "Follow project instructions." in str(messages[1].content)
    assert messages[2].is_meta is True
    assert "# readme" in str(messages[2].content)
    assert messages[-1] == session[0]


def test_context_builder_ignores_secret_files(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("KGENT_API_KEY=secret", encoding="utf-8")
    (tmp_path / "README.md").write_text("public docs", encoding="utf-8")

    messages = build_model_messages([Message(role="user", content="hello")], project_root=tmp_path)
    joined = _joined(messages)

    assert "public docs" in joined
    assert "KGENT_API_KEY" not in joined
    assert "secret" not in joined


def test_build_model_messages_strips_legacy_session_system(tmp_path: Path) -> None:
    session = [
        Message(role="system", content="legacy system prompt"),
        Message(role="user", content="hello"),
    ]

    messages = build_model_messages(session, project_root=tmp_path)

    assert [message.role for message in messages].count("system") == 1
    assert "legacy system prompt" not in _joined(messages)
    assert messages[-1].content == "hello"


def test_tool_result_stays_in_session_messages_not_system_context(tmp_path: Path) -> None:
    tool_use = ToolUseBlock(id="toolu_1", name="read_file", input={"path": "README.md"})
    tool_result = ToolResultBlock(tool_use_id="toolu_1", content="unique_result_abc123", is_error=False)
    session = [
        Message(role="user", content="read README"),
        Message(role="assistant", content=[tool_use], assistant_text="reading"),
        Message(role="user", content=[tool_result]),
    ]

    messages = build_model_messages(session, project_root=tmp_path)

    assert isinstance(messages[0].content, str)
    assert "unique_result_abc123" not in messages[0].content
    assert any(
        message.role == "user"
        and isinstance(message.content, list)
        and message.content
        and isinstance(message.content[0], ToolResultBlock)
        for message in messages
    )


def test_build_context_bundle_loads_instruction_files_in_order(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("claude rules", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("agent rules", encoding="utf-8")
    (tmp_path / "KGENT.md").write_text("kgent rules", encoding="utf-8")

    bundle = build_context_bundle(tmp_path)
    instructions = bundle.user_context["projectInstructions"]

    assert instructions.index("# CLAUDE.md") < instructions.index("# AGENTS.md")
    assert instructions.index("# AGENTS.md") < instructions.index("# KGENT.md")
