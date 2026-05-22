"""Write project-local UTF-8 text files."""

from pathlib import Path
from typing import Any

from app.tools.path_safety import ensure_not_protected, ensure_safe_parent_dirs, safe_resolve


class WriteFileTool:
    name = "write_file"
    description = "Write UTF-8 text content to a project-relative file path."
    risk_level = "high"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Project-relative file path.",
            },
            "content": {
                "type": "string",
                "description": "Full UTF-8 text content to write.",
            },
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        raw_path = input.get("path")
        content = input.get("content")
        if not isinstance(content, str):
            raise ValueError("write_file requires a 'content' string")

        target = safe_resolve(self.project_root, raw_path, tool_name=self.name)
        ensure_not_protected(target, raw_path)
        ensure_safe_parent_dirs(self.project_root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        relative = target.relative_to(self.project_root)
        byte_count = len(content.encode("utf-8"))
        return f"written: {relative.as_posix()}\nchars: {len(content)}\nbytes: {byte_count}"
