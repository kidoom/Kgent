"""List files under the configured project root."""

from pathlib import Path
from typing import Any

from app.tools.path_safety import safe_resolve


class ListFilesTool:
    name = "list_files"
    description = "List files and directories under a project-relative path."
    risk_level = "low"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Project-relative directory path. Defaults to '.'.",
            }
        },
        "required": [],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        raw_path = input.get("path", ".")
        target = safe_resolve(self.project_root, raw_path, tool_name=self.name)
        if not target.exists():
            raise FileNotFoundError(f"path not found: {raw_path}")
        if not target.is_dir():
            raise NotADirectoryError(f"path is not a directory: {raw_path}")

        entries = []
        for child in sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
            if child.name.startswith("."):
                continue
            suffix = "/" if child.is_dir() else ""
            entries.append(f"{child.name}{suffix}")
        return "\n".join(entries) if entries else "<empty directory>"
