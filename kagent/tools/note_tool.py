"""NoteTool — structured note CRUD for Agent."""

import json
from datetime import datetime, timezone
from typing import Optional

from .base import Tool, ToolResult, ToolParameter


class NoteTool(Tool):
    """Simple in-memory note storage with CRUD operations.

    Actions: create, read, update, delete, list
    """

    def __init__(self):
        super().__init__(
            name="notes",
            description="笔记工具 — 创建、读取、更新、删除笔记",
        )
        self._notes: dict[str, dict] = {}  # id → {title, content, created_at, updated_at}
        self._counter = 0

    def run(self, parameters: dict) -> ToolResult:
        action = parameters.get("action", "").strip().lower()

        if action == "create":
            return self._create(parameters)
        elif action == "read":
            return self._read(parameters)
        elif action == "update":
            return self._update(parameters)
        elif action == "delete":
            return self._delete(parameters)
        elif action == "list":
            return self._list()
        else:
            return ToolResult(
                content=f"[ERROR] 未知操作: '{action}'，支持: create, read, update, delete, list",
                success=False,
                error="invalid_action",
            )

    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(name="action", type="string",
                          description="操作: create/read/update/delete/list", required=True),
            ToolParameter(name="id", type="string",
                          description="笔记 ID (read/update/delete 时必填)", required=False),
            ToolParameter(name="title", type="string",
                          description="笔记标题 (create/update 时使用)", required=False),
            ToolParameter(name="content", type="string",
                          description="笔记内容 (create/update 时使用)", required=False),
        ]

    def _create(self, params: dict) -> ToolResult:
        title = params.get("title", "Untitled").strip()
        content = params.get("content", "").strip()
        self._counter += 1
        note_id = str(self._counter)
        now = datetime.now(timezone.utc).isoformat()
        self._notes[note_id] = {
            "id": note_id, "title": title, "content": content,
            "created_at": now, "updated_at": now,
        }
        return ToolResult(
            content=f"笔记已创建: id={note_id}, title={title}",
            success=True,
            metadata={"id": note_id},
        )

    def _read(self, params: dict) -> ToolResult:
        note_id = params.get("id", "").strip()
        note = self._notes.get(note_id)
        if not note:
            return ToolResult(
                content=f"[ERROR] 笔记 '{note_id}' 不存在",
                success=False,
                error="not_found",
            )
        return ToolResult(
            content=json.dumps(note, ensure_ascii=False, indent=2),
            success=True,
        )

    def _update(self, params: dict) -> ToolResult:
        note_id = params.get("id", "").strip()
        note = self._notes.get(note_id)
        if not note:
            return ToolResult(
                content=f"[ERROR] 笔记 '{note_id}' 不存在",
                success=False,
                error="not_found",
            )
        if "title" in params:
            note["title"] = params["title"]
        if "content" in params:
            note["content"] = params["content"]
        note["updated_at"] = datetime.now(timezone.utc).isoformat()
        return ToolResult(
            content=f"笔记 '{note_id}' 已更新",
            success=True,
        )

    def _delete(self, params: dict) -> ToolResult:
        note_id = params.get("id", "").strip()
        if note_id not in self._notes:
            return ToolResult(
                content=f"[ERROR] 笔记 '{note_id}' 不存在",
                success=False,
                error="not_found",
            )
        del self._notes[note_id]
        return ToolResult(
            content=f"笔记 '{note_id}' 已删除",
            success=True,
        )

    def _list(self) -> ToolResult:
        if not self._notes:
            return ToolResult(content="没有笔记", success=True)
        lines = []
        for n in self._notes.values():
            lines.append(f"- [{n['id']}] {n['title']}")
        return ToolResult(content="\n".join(lines), success=True)
