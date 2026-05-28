"""Tool registry for Kgent V0.1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Coroutine

from app.tools.base import Tool, tool_to_schema
from app.tools.bash import BashTool
from app.tools.calculator import CalculatorTool
from app.tools.edit_file import EditFileTool
from app.tools.git_diff import GitDiffTool
from app.tools.git_log import GitLogTool
from app.tools.git_status import GitStatusTool
from app.tools.grep import GrepTool
from app.tools.list_files import ListFilesTool
from app.tools.read_file import ReadFileTool
from app.tools.task import TaskTool
from app.tools.todo_write import TodoWriteTool
from app.tools.web_fetch import WebFetchTool
from app.tools.write_file import WriteFileTool
from app.memory.persistence import PersistenceService
from app.runtime.todo_state import TodoStateStore


def build_tools(
    project_root: Path,
    *,
    session_id: str = "default",
    todo_state_store: TodoStateStore | None = None,
    persistence: PersistenceService | None = None,
    subagent_runner: Callable[..., Coroutine[Any, Any, Any]] | None = None,
    include_task_tool: bool = False,
) -> list[Tool]:
    tools: list[Tool] = [
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
        GrepTool(project_root=project_root),
        BashTool(),
        WebFetchTool(),
        GitStatusTool(project_root=project_root),
        GitDiffTool(project_root=project_root),
        GitLogTool(project_root=project_root),
    ]
    if include_task_tool and subagent_runner is not None:
        tools.append(TaskTool(runner=subagent_runner))
    return tools


def build_subagent_runner(
    *,
    model_client: Any,
    parent_session_id: str,
    project_root: Path,
    policy: Any = None,
    persistence: PersistenceService | None = None,
    todo_state_store: TodoStateStore | None = None,
) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Build a runner closure for TaskTool that delegates to run_subagent.

    The returned async callable accepts ``prompt`` and optional ``max_steps``.
    It constructs child tools bound to the child session id (so TodoWriteTool
    writes to the child, not the parent).  The active parent host is picked up
    from the ``subagent_active_host`` context variable, so permission requests
    in the child can bubble up to the parent UI.
    """
    from app.runtime.subagent import run_subagent

    async def _runner(*, prompt: str, max_steps: int | None = None) -> Any:
        def _build_child_tools(child_session_id: str) -> list[Tool]:
            return build_tools(
                project_root,
                session_id=child_session_id,
                todo_state_store=todo_state_store,
                persistence=persistence,
            )

        return await run_subagent(
            prompt=prompt,
            parent_session_id=parent_session_id,
            model_client=model_client,
            build_child_tools=_build_child_tools,
            policy=policy,
            project_root=project_root,
            persistence=persistence,
            max_steps=max_steps or 5,
        )

    return _runner


def find_tool_by_name(tools: list[Tool], name: str) -> Tool | None:
    for tool in tools:
        if tool.name == name:
            return tool
    return None


def build_tool_schemas(tools: list[Tool]) -> list[dict]:
    return [tool_to_schema(tool) for tool in tools]
