"""Show git diff of changes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any


class GitDiffTool:
    name = "git_diff"
    description = "Show diff of changes. Pass staged=true for staged changes."
    risk_level = "low"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "staged": {
                "type": "boolean",
                "description": "If true, show staged changes (git diff --cached). Default: false.",
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    async def call(self, input: dict[str, Any]) -> str:
        staged = input.get("staged", False)
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except FileNotFoundError:
            return "[error: git not found]"
        except asyncio.TimeoutError:
            return "[error: git diff timed out]"

        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            return f"[git error: {err}]"

        output = stdout.decode(errors="replace").strip()
        return output or "<no changes>"
