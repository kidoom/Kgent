"""TerminalTool — restricted filesystem operations (read/list only)."""

import os
from pathlib import Path

from .base import Tool, ToolResult, ToolParameter


class TerminalTool(Tool):
    """Restricted filesystem tool — only read and list operations.

    Actions:
      - list: List files in a directory
      - read: Read file contents (text files only, max 10KB)

    Write/delete/execute operations are NOT supported for safety.
    """

    def __init__(self, root_dir: str = "."):
        super().__init__(
            name="terminal",
            description="文件系统工具 — 列出目录文件、读取文件内容（只读）",
        )
        self._root = Path(root_dir).resolve()

    def run(self, parameters: dict) -> ToolResult:
        action = parameters.get("action", "").strip().lower()

        if action == "list":
            return self._list(parameters)
        elif action == "read":
            return self._read(parameters)
        else:
            return ToolResult(
                content=f"[ERROR] 未知操作: '{action}'，支持: list, read",
                success=False,
                error="invalid_action",
            )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="action", type="string",
                          description="操作: list (列出目录) / read (读取文件)", required=True),
            ToolParameter(name="path", type="string",
                          description="目标路径 (相对于根目录)", required=False),
        ]

    def _list(self, params: dict) -> ToolResult:
        rel_path = params.get("path", ".").strip()
        target = (self._root / rel_path).resolve()

        # Security: ensure target is under root
        if not str(target).startswith(str(self._root)):
            return ToolResult(
                content="[ERROR] 路径越界: 不能访问根目录之外的文件",
                success=False,
                error="path_escape",
            )

        if not target.exists():
            return ToolResult(
                content=f"[ERROR] 路径不存在: {rel_path}",
                success=False,
                error="not_found",
            )

        if target.is_file():
            return ToolResult(content=f"[文件] {target.name}", success=True)

        entries = []
        for item in sorted(target.iterdir()):
            prefix = "[目录]" if item.is_dir() else "[文件]"
            entries.append(f"{prefix} {item.name}")
        return ToolResult(
            content="\n".join(entries) if entries else "(空目录)",
            success=True,
        )

    def _read(self, params: dict) -> ToolResult:
        rel_path = params.get("path", "").strip()
        if not rel_path:
            return ToolResult(
                content="[ERROR] read 操作需要 path 参数",
                success=False,
                error="missing_path",
            )

        target = (self._root / rel_path).resolve()

        # Security check
        if not str(target).startswith(str(self._root)):
            return ToolResult(
                content="[ERROR] 路径越界",
                success=False,
                error="path_escape",
            )

        if not target.exists():
            return ToolResult(
                content=f"[ERROR] 文件不存在: {rel_path}",
                success=False,
                error="not_found",
            )

        if not target.is_file():
            return ToolResult(
                content=f"[ERROR] '{rel_path}' 不是文件",
                success=False,
                error="not_file",
            )

        # Size limit: 10KB
        size = target.stat().st_size
        if size > 10240:
            return ToolResult(
                content=f"[ERROR] 文件过大 ({size} bytes)，限制 10KB",
                success=False,
                error="file_too_large",
            )

        try:
            text = target.read_text(encoding="utf-8")
            return ToolResult(
                content=text,
                success=True,
                metadata={"path": rel_path, "size": size},
            )
        except UnicodeDecodeError:
            return ToolResult(
                content=f"[ERROR] 文件 '{rel_path}' 不是文本文件",
                success=False,
                error="binary_file",
            )
