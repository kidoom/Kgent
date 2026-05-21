"""List files under the configured project root."""

from pathlib import Path
from typing import Any


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
        if not isinstance(raw_path, str):
            raise ValueError("list_files 'path' must be a string")
        target = _safe_resolve(self.project_root, raw_path)
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


def _safe_resolve(project_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must be project-relative and cannot contain '..'")
    if any(part.startswith(".") for part in candidate.parts if part not in {"."}):
        raise ValueError("path cannot reference hidden files or directories")
    resolved = (project_root / candidate).resolve()
    if project_root != resolved and project_root not in resolved.parents:
        raise ValueError("path escapes project root")
    return resolved
