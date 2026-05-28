"""Execute shell commands with timeout and output capture."""

from __future__ import annotations

import asyncio
from typing import Any

_DEFAULT_TIMEOUT = 30


class BashTool:
    name = "bash"
    description = (
        "Execute a shell command and return its output. "
        "Supports pipes, redirects, and chaining. "
        f"Default timeout is {_DEFAULT_TIMEOUT} seconds."
    )
    risk_level = "high"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": f"Timeout in seconds (default: {_DEFAULT_TIMEOUT}).",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    async def call(self, input: dict[str, Any]) -> str:
        command = input.get("command")
        if not command:
            raise ValueError("bash requires a 'command' string")

        timeout = int(input.get("timeout", _DEFAULT_TIMEOUT))

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return f"[timeout: command exceeded {timeout}s]"

        parts: list[str] = []
        if stdout:
            parts.append(stdout.decode(errors="replace"))
        if stderr:
            parts.append(stderr.decode(errors="replace"))
        output = "".join(parts)

        if proc.returncode != 0:
            output += f"\n[exit code: {proc.returncode}]"

        return output.strip() or "<no output>"
