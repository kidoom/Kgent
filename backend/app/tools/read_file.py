"""Read project-local text files."""

from pathlib import Path
from typing import Any

from app.tools.path_safety import ensure_not_protected, safe_resolve


class ReadFileTool:
    name = "read_file"
    description = "Read a UTF-8 text file from the project directory."
    risk_level = "medium"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Project-relative file path, for example README.md.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path, max_chars: int = 20_000):
        self.project_root = project_root.resolve()
        self.max_chars = max_chars

    async def call(self, input: dict[str, Any]) -> str:
        raw_path = input.get("path")
        target = safe_resolve(self.project_root, raw_path, tool_name=self.name)
        ensure_not_protected(target, raw_path)
        if not target.exists():
            raise FileNotFoundError(f"file not found: {raw_path}")
        if not target.is_file():
            raise IsADirectoryError(f"path is not a file: {raw_path}")
        content = target.read_text(encoding="utf-8-sig")
        if len(content) > self.max_chars:
            return content[: self.max_chars] + "\n...[truncated]"
        return content
