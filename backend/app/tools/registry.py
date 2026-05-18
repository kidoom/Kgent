"""Tool registry for Kgent V0.1."""

from pathlib import Path

from app.tools.base import Tool, tool_to_schema
from app.tools.calculator import CalculatorTool
from app.tools.list_files import ListFilesTool
from app.tools.read_file import ReadFileTool


def build_tools(project_root: Path) -> list[Tool]:
    return [
        CalculatorTool(),
        ListFilesTool(project_root=project_root),
        ReadFileTool(project_root=project_root),
    ]


def find_tool_by_name(tools: list[Tool], name: str) -> Tool | None:
    for tool in tools:
        if tool.name == name:
            return tool
    return None


def build_tool_schemas(tools: list[Tool]) -> list[dict]:
    return [tool_to_schema(tool) for tool in tools]
