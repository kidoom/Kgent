"""TodoWrite planning tool (M0.5.2)."""

from __future__ import annotations

from typing import Any

from app.memory.persistence import PersistenceService
from app.runtime.todo_state import TodoStateStore, format_todo_items, validate_todo_items


class TodoWriteTool:
    name = "todo_write"
    description = (
        "Create or update the current session todo list. Use it for multi-step work, "
        "keeping at most one item in_progress."
    )
    risk_level = "low"
    input_schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "Full replacement todo list for the current session.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Stable todo id."},
                        "text": {"type": "string", "description": "Todo description."},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                        },
                    },
                    "required": ["id", "text", "status"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        session_id: str = "default",
        state_store: TodoStateStore | None = None,
        persistence: PersistenceService | None = None,
    ) -> None:
        self.session_id = session_id
        self.state_store = state_store or TodoStateStore()
        self.persistence = persistence

    async def call(self, input: dict[str, Any]) -> str:
        items = validate_todo_items(input.get("items"))
        state = self.state_store.set_items(self.session_id, items)
        if self.persistence is not None:
            self.persistence.append_todo_state(self.session_id, state.model_dump(mode="json"))
        return format_todo_items(items)
