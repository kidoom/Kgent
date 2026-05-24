"""Tool registry for Kgent V0.1."""

from pathlib import Path

from app.tools.base import Tool, tool_to_schema
from app.tools.calculator import CalculatorTool
from app.tools.edit_file import EditFileTool
from app.tools.list_files import ListFilesTool
from app.tools.read_file import ReadFileTool
from app.tools.todo_write import TodoWriteTool
from app.tools.write_file import WriteFileTool
from app.memory.persistence import PersistenceService
from app.runtime.todo_state import TodoStateStore


def build_tools(
    project_root: Path,
    *,
    session_id: str = "default",
    todo_state_store: TodoStateStore | None = None,
    persistence: PersistenceService | None = None,
) -> list[Tool]:
    return [
        TodoWriteTool(
            session_id=session_id,
            state_store=todo_state_store,
            persistence=persistence,
        ),
        CalculatorTool(),
        ListFilesTool(project_root=project_root),
        ReadFileTool(project_root=project_root),
        WriteFileTool(project_root=project_root),
        EditFileTool(project_root=project_root),
    ]


def find_tool_by_name(tools: list[Tool], name: str) -> Tool | None:
    for tool in tools:
        if tool.name == name:
            return tool
    return None


def build_tool_schemas(tools: list[Tool]) -> list[dict]:
    return [tool_to_schema(tool) for tool in tools]
