"""Search file contents by regex pattern within the project directory."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.tools.path_safety import safe_resolve

_DEFAULT_MAX_RESULTS = 50


class GrepTool:
    name = "grep"
    description = (
        "Search file contents by regex pattern. Returns matching lines "
        "with file paths and line numbers."
    )
    risk_level = "low"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Python regex pattern to search for.",
            },
            "path": {
                "type": "string",
                "description": "Project-relative directory or file path to search in. Defaults to '.'.",
            },
            "glob": {
                "type": "string",
                "description": "File extension filter, e.g. '*.py'. Searches all files if omitted.",
            },
            "max_results": {
                "type": "integer",
                "description": f"Maximum number of matches to return (default: {_DEFAULT_MAX_RESULTS}).",
            },
        },
        "required": ["pattern"],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        pattern = input.get("pattern")
        if not pattern:
            raise ValueError("grep requires a 'pattern' string")

        raw_path = input.get("path", ".")
        target = safe_resolve(self.project_root, raw_path, tool_name=self.name)

        glob_filter = input.get("glob")
        max_results = int(input.get("max_results", _DEFAULT_MAX_RESULTS))

        try:
            regex = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"invalid regex pattern: {exc}") from exc

        matches: list[str] = []
        files = self._collect_files(target, glob_filter)
        for filepath in files:
            try:
                text = filepath.read_text(encoding="utf-8-sig", errors="replace")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    rel = filepath.relative_to(self.project_root)
                    matches.append(f"{rel}:{lineno}: {line}")
                    if len(matches) >= max_results:
                        return "\n".join(matches)

        return "\n".join(matches) if matches else "<no matches>"

    def _collect_files(self, target: Path, glob_filter: str | None) -> list[Path]:
        if target.is_file():
            return [target]
        if not target.is_dir():
            return []
        if glob_filter:
            return sorted(target.rglob(glob_filter))
        return sorted(
            p for p in target.rglob("*")
            if p.is_file() and not p.name.startswith(".")
        )
