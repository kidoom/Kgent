"""Shared project-local path safety helpers for file tools."""

from __future__ import annotations

from pathlib import Path

DENIED_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.staging",
        ".env.development",
        ".env.test",
        ".env.backup",
    }
)
DENIED_EXTENSIONS = frozenset(
    {
        ".key",
        ".pem",
        ".p12",
        ".pfx",
        ".crt",
        ".cer",
        ".jks",
        ".keystore",
        ".secret",
        ".credentials",
    }
)


def require_relative_path(raw_path: object, *, tool_name: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"{tool_name} requires a non-empty 'path' string")
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path must be project-relative and cannot contain '..'")
    if any(part.startswith(".") for part in candidate.parts if part not in {"."}):
        raise ValueError("path cannot reference hidden files or directories")
    return candidate


def safe_resolve(project_root: Path, raw_path: object, *, tool_name: str) -> Path:
    candidate = require_relative_path(raw_path, tool_name=tool_name)
    root = project_root.resolve()
    resolved = (root / candidate).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("path escapes project root")
    return resolved


def is_protected_path(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if ".git" in lowered_parts:
        return True
    name = path.name.lower()
    if name in DENIED_NAMES:
        return True
    if name.startswith(".env."):
        return True
    if path.suffix.lower() in DENIED_EXTENSIONS:
        return True
    return False


def ensure_not_protected(path: Path, raw_path: object) -> None:
    if is_protected_path(path):
        raise ValueError(f"access denied: {raw_path} is a protected file")


def ensure_safe_parent_dirs(project_root: Path, target: Path) -> None:
    root = project_root.resolve()
    for parent in target.parents:
        if parent == root:
            break
        if root not in parent.parents:
            continue
        relative = parent.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            raise ValueError("path cannot reference hidden files or directories")
        if is_protected_path(parent):
            raise ValueError(f"access denied: {relative} is a protected path")
