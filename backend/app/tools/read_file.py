"""Read project-local text files."""

from pathlib import Path
from typing import Any

# Files the agent must never read — secrets, credentials, env vars.
_DENIED_NAMES = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging", ".env.development",
    ".env.test", ".env.backup",
})
_DENIED_EXTENSIONS = frozenset({
    ".key", ".pem", ".p12", ".pfx", ".crt", ".cer", ".jks",
    ".keystore", ".secret", ".credentials",
})


def _is_denied(path: Path) -> bool:
    name = path.name.lower()
    if name in _DENIED_NAMES:
        return True
    if name.startswith(".env."):
        return True
    if path.suffix.lower() in _DENIED_EXTENSIONS:
        return True
    return False


class ReadFileTool:
    name = "read_file"
    description = "Read a UTF-8 text file from the project directory."
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
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("read_file requires a non-empty 'path' string")
        target = _safe_resolve(self.project_root, raw_path)
        if _is_denied(target):
            raise ValueError(f"access denied: {raw_path} is a protected file")
        if not target.exists():
            raise FileNotFoundError(f"file not found: {raw_path}")
        if not target.is_file():
            raise IsADirectoryError(f"path is not a file: {raw_path}")
        content = target.read_text(encoding="utf-8-sig")
        if len(content) > self.max_chars:
            return content[: self.max_chars] + "\n...[truncated]"
        return content


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
