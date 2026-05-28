"""Show recent git commit history."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

_DEFAULT_COUNT = 20


class GitLogTool:
    name = "git_log"
    description = f"Show recent commit history (default {_DEFAULT_COUNT} commits)."
    risk_level = "low"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": f"Number of commits to show (default: {_DEFAULT_COUNT}).",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        count = int(input.get("count", _DEFAULT_COUNT))

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "log", f"--oneline", f"-{count}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except FileNotFoundError:
            return "[error: git not found]"
        except asyncio.TimeoutError:
            return "[error: git log timed out]"

        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            return f"[git error: {err}]"

        output = stdout.decode(errors="replace").strip()
        return output or "<no commits>"
