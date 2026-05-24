"""Session-local TodoWrite state for planning support (M0.5.2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.runtime.messages import Message

TodoStatus = Literal["pending", "in_progress", "completed"]


class TodoItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    status: TodoStatus


class TodoState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TodoItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    rounds_since_todo_write: int = 0

    @property
    def has_incomplete_items(self) -> bool:
        return any(item.status != "completed" for item in self.items)


class TodoStateStore:
    def __init__(self) -> None:
        self._states: dict[str, TodoState] = {}

    def get_state(self, session_id: str) -> TodoState:
        return self._states.setdefault(session_id, TodoState())

    def set_items(self, session_id: str, items: list[TodoItem]) -> TodoState:
        state = TodoState(
            items=items,
            updated_at=datetime.now(timezone.utc),
            rounds_since_todo_write=0,
        )
        self._states[session_id] = state
        return state

    def hydrate(self, session_id: str, payload: dict | None) -> TodoState:
        if payload is None:
            return self.get_state(session_id)
        state = TodoState.model_validate(payload)
        self._states[session_id] = state
        return state

    def forget(self, session_id: str) -> None:
        self._states.pop(session_id, None)

    def reset(self) -> None:
        self._states.clear()

    def record_model_turn_without_todo_write(self, session_id: str) -> TodoState:
        state = self.get_state(session_id)
        state.rounds_since_todo_write += 1
        return state

    def reminder_message(self, session_id: str, *, threshold: int = 3) -> Message | None:
        state = self.get_state(session_id)
        if not state.has_incomplete_items or state.rounds_since_todo_write < threshold:
            return None
        compact = format_todo_items(state.items)
        return Message(
            role="user",
            content=(
                "<todo_reminder>\n"
                "Update todo_write before continuing. Keep exactly one task in_progress.\n"
                f"{compact}\n"
                "</todo_reminder>"
            ),
            is_meta=True,
        )


def validate_todo_items(raw_items: object) -> list[TodoItem]:
    if not isinstance(raw_items, list):
        raise ValueError("todo_write requires 'items' to be a list")
    items: list[TodoItem] = []
    seen_ids: set[str] = set()
    in_progress_count = 0
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("each todo item must be an object")
        item = TodoItem.model_validate(raw)
        item_id = item.id.strip()
        text = item.text.strip()
        if not item_id:
            raise ValueError("todo item id must be non-empty")
        if not text:
            raise ValueError("todo item text must be non-empty")
        if item_id in seen_ids:
            raise ValueError(f"duplicate todo item id: {item_id}")
        seen_ids.add(item_id)
        if item.status == "in_progress":
            in_progress_count += 1
        items.append(TodoItem(id=item_id, text=text, status=item.status))
    if in_progress_count > 1:
        raise ValueError("todo_write allows at most one in_progress item")
    return items


def format_todo_items(items: list[TodoItem]) -> str:
    if not items:
        return "(todo list cleared)"
    markers = {
        "pending": "[ ]",
        "in_progress": "[>]",
        "completed": "[x]",
    }
    return "\n".join(f"{markers[item.status]} {item.id}: {item.text}" for item in items)
