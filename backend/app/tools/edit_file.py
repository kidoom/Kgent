"""Apply a single safe text replacement to a project-local UTF-8 file."""

from pathlib import Path
from typing import Any

from app.tools.path_safety import ensure_not_protected, safe_resolve


class EditFileTool:
    name = "edit_file"
    description = "Replace exactly one text occurrence in a project-relative UTF-8 file."
    risk_level = "high"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Project-relative file path.",
            },
            "old_text": {
                "type": "string",
                "description": "Existing text that must occur exactly once.",
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text.",
            },
        },
        "required": ["path", "old_text", "new_text"],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        raw_path = input.get("path")
        old_text = input.get("old_text")
        new_text = input.get("new_text")
        if not isinstance(old_text, str) or old_text == "":
            raise ValueError("edit_file requires a non-empty 'old_text' string")
        if not isinstance(new_text, str):
            raise ValueError("edit_file requires a 'new_text' string")

        target = safe_resolve(self.project_root, raw_path, tool_name=self.name)
        ensure_not_protected(target, raw_path)
        if not target.exists():
            raise FileNotFoundError(f"file not found: {raw_path}")
        if not target.is_file():
            raise IsADirectoryError(f"path is not a file: {raw_path}")

        content = target.read_text(encoding="utf-8")
        occurrences = content.count(old_text)
        if occurrences == 0:
            raise ValueError("old_text was not found")
        if occurrences > 1:
            raise ValueError("old_text occurs more than once; edit is ambiguous")

        target.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
        relative = target.relative_to(self.project_root)
        return (
            f"edited: {relative.as_posix()}\n"
            "replaced: 1 occurrence\n"
            f"old_chars: {len(old_text)}\n"
            f"new_chars: {len(new_text)}"
        )
