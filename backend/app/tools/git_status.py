"""Show git working tree status."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


class GitStatusTool:
    name = "git_status"
    description = "Show git working tree status (staged, unstaged, untracked files)."
    risk_level = "low"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "status", "--short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except FileNotFoundError:
            return "[error: git not found]"
        except asyncio.TimeoutError:
            return "[error: git status timed out]"

        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            return f"[git error: {err}]"

        output = stdout.decode(errors="replace").strip()
        return output or "working tree clean"
