"""Context assembly for model requests (M0.4).

Kgent mirrors Claude Code's separation here: session history stores only real
conversation messages, while system/user context is built just-in-time before a
model request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.runtime.messages import Message
from app.runtime.prompts import SYSTEM_PROMPT
from app.tools.path_safety import ensure_not_protected, safe_resolve

PROJECT_INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md", "KGENT.md")
README_FILES = ("README.md", "README.txt")
DEFAULT_MAX_CONTEXT_CHARS = 12_000
DEFAULT_MAX_FILE_CHARS = 4_000


@dataclass(frozen=True)
class ContextBundle:
    system_prompt: str
    system_context: dict[str, str]
    user_context: dict[str, str]


def build_context_bundle(
    project_root: Path,
    *,
    max_file_chars: int = DEFAULT_MAX_FILE_CHARS,
) -> ContextBundle:
    root = project_root.resolve()
    project_instructions = _load_project_instructions(root, max_file_chars=max_file_chars)
    readme = _load_first_existing(root, README_FILES, max_chars=max_file_chars)
    return ContextBundle(
        system_prompt=SYSTEM_PROMPT,
        system_context={
            "projectRoot": str(root),
            "runtime": "Kgent runs a serial model-tool-observe loop with HTTP commands and SSE events.",
            "fileSafety": (
                "All file tools are restricted to project-relative paths inside projectRoot. "
                "Hidden paths, .env files, .git, and certificate/key/credential files are protected."
            ),
            "toolPolicy": (
                "Tool risk levels are runtime metadata. low/medium tools may run under risk_based; "
                "high tools such as write_file and edit_file require allow_all or explicit user approval."
            ),
        },
        user_context={
            **({"projectInstructions": project_instructions} if project_instructions else {}),
            **({"readme": readme} if readme else {}),
            "currentDate": f"Today's date is {date.today().isoformat()}.",
        },
    )


def build_model_messages(
    session_messages: list[Message],
    *,
    project_root: Path,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> list[Message]:
    bundle = build_context_bundle(project_root)
    system_message = Message(
        role="system",
        content=_append_system_context(bundle.system_prompt, bundle.system_context),
    )
    context_messages = _prepend_user_context(bundle.user_context, max_context_chars=max_context_chars)
    return [system_message, *context_messages, *_strip_legacy_system_messages(session_messages)]


def _append_system_context(system_prompt: str, context: dict[str, str]) -> str:
    context_text = "\n".join(f"{key}: {value}" for key, value in context.items() if value)
    if not context_text:
        return system_prompt
    return f"{system_prompt.rstrip()}\n\n{context_text}"


def _prepend_user_context(context: dict[str, str], *, max_context_chars: int) -> list[Message]:
    messages: list[Message] = []
    project_instructions = context.get("projectInstructions")
    if project_instructions:
        messages.append(
            Message(
                role="user",
                content=f"<project-instructions>\n{project_instructions}\n</project-instructions>\n",
                is_meta=True,
            )
        )

    reminder_entries = [(key, value) for key, value in context.items() if key != "projectInstructions" and value]
    if reminder_entries:
        body = "\n".join(f"# {key}\n{value}" for key, value in reminder_entries)
        body = _truncate(body, max_context_chars)
        messages.append(
            Message(
                role="user",
                content=(
                    "<system-reminder>\n"
                    "As you answer the user's request, you can use the following context:\n"
                    f"{body}\n\n"
                    "IMPORTANT: this context may or may not be relevant. Do not mention it unless it helps the task.\n"
                    "</system-reminder>\n"
                ),
                is_meta=True,
            )
        )
    return messages


def _strip_legacy_system_messages(messages: list[Message]) -> list[Message]:
    return [message for message in messages if message.role != "system"]


def _load_project_instructions(project_root: Path, *, max_file_chars: int) -> str | None:
    parts: list[str] = []
    for name in PROJECT_INSTRUCTION_FILES:
        content = _load_safe_text_file(project_root, name, max_chars=max_file_chars)
        if content:
            parts.append(f"# {name}\n{content}")
    return "\n\n".join(parts) if parts else None


def _load_first_existing(project_root: Path, names: tuple[str, ...], *, max_chars: int) -> str | None:
    for name in names:
        content = _load_safe_text_file(project_root, name, max_chars=max_chars)
        if content:
            return content
    return None


def _load_safe_text_file(project_root: Path, raw_path: str, *, max_chars: int) -> str | None:
    try:
        target = safe_resolve(project_root, raw_path, tool_name="context_builder")
        ensure_not_protected(target, raw_path)
    except ValueError:
        return None
    if not target.exists() or not target.is_file():
        return None
    try:
        content = target.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return None
    return _truncate(content, max_chars)


def _truncate(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n...[truncated]"
