from pathlib import Path

import pytest

from app.tools.base import tool_to_schema
from app.tools.calculator import CalculatorTool
from app.tools.edit_file import EditFileTool
from app.tools.list_files import ListFilesTool
from app.tools.read_file import ReadFileTool
from app.tools.registry import build_tools, find_tool_by_name
from app.tools.todo_write import TodoWriteTool
from app.tools.write_file import WriteFileTool
from app.runtime.todo_state import TodoStateStore


@pytest.mark.asyncio
async def test_calculator_evaluates_safe_expression() -> None:
    result = await CalculatorTool().call({"expression": "12 * 8 + 6"})
    assert result == "102"


@pytest.mark.asyncio
async def test_read_file_blocks_parent_traversal(tmp_path: Path) -> None:
    tool = ReadFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": "../secret.txt"})


@pytest.mark.asyncio
async def test_read_file_blocks_env_file(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("KGENT_API_KEY=secret", encoding="utf-8")
    tool = ReadFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": ".env"})


@pytest.mark.asyncio
async def test_read_file_blocks_hidden_directory(tmp_path: Path) -> None:
    hidden_dir = tmp_path / ".git"
    hidden_dir.mkdir()
    (hidden_dir / "config").write_text("token=secret", encoding="utf-8")
    tool = ReadFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": ".git/config"})


@pytest.mark.asyncio
async def test_list_files_hides_hidden_entries(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("KGENT_API_KEY=secret", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    tool = ListFilesTool(project_root=tmp_path)

    result = await tool.call({"path": "."})

    assert "README.md" in result
    assert ".env" not in result


@pytest.mark.asyncio
async def test_list_files_blocks_hidden_directory(tmp_path: Path) -> None:
    hidden_dir = tmp_path / ".git"
    hidden_dir.mkdir()
    (hidden_dir / "config").write_text("token=secret", encoding="utf-8")
    tool = ListFilesTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": ".git"})


@pytest.mark.asyncio
async def test_write_file_writes_project_file(tmp_path: Path) -> None:
    tool = WriteFileTool(project_root=tmp_path)

    result = await tool.call({"path": "notes/todo.txt", "content": "ship it"})

    assert (tmp_path / "notes" / "todo.txt").read_text(encoding="utf-8") == "ship it"
    assert "written: notes/todo.txt" in result
    assert "chars: 7" in result


@pytest.mark.asyncio
async def test_write_file_blocks_parent_traversal(tmp_path: Path) -> None:
    tool = WriteFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": "../secret.txt", "content": "nope"})


@pytest.mark.asyncio
async def test_write_file_blocks_protected_env_file(tmp_path: Path) -> None:
    tool = WriteFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": ".env", "content": "KGENT_API_KEY=secret"})

    assert not (tmp_path / ".env").exists()


@pytest.mark.asyncio
async def test_write_file_blocks_hidden_directory(tmp_path: Path) -> None:
    tool = WriteFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": ".git/config", "content": "token=secret"})


@pytest.mark.asyncio
async def test_edit_file_replaces_unique_text(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("hello old world", encoding="utf-8")
    tool = EditFileTool(project_root=tmp_path)

    result = await tool.call({"path": "README.md", "old_text": "old", "new_text": "new"})

    assert target.read_text(encoding="utf-8") == "hello new world"
    assert "edited: README.md" in result
    assert "replaced: 1 occurrence" in result


@pytest.mark.asyncio
async def test_edit_file_missing_old_text_does_not_mutate(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("hello world", encoding="utf-8")
    tool = EditFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": "README.md", "old_text": "missing", "new_text": "new"})

    assert target.read_text(encoding="utf-8") == "hello world"


@pytest.mark.asyncio
async def test_edit_file_duplicate_old_text_does_not_mutate(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("old and old", encoding="utf-8")
    tool = EditFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": "README.md", "old_text": "old", "new_text": "new"})

    assert target.read_text(encoding="utf-8") == "old and old"


@pytest.mark.asyncio
async def test_edit_file_blocks_protected_env_file(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("KGENT_API_KEY=secret", encoding="utf-8")
    tool = EditFileTool(project_root=tmp_path)

    with pytest.raises(ValueError):
        await tool.call({"path": ".env", "old_text": "secret", "new_text": "public"})

    assert target.read_text(encoding="utf-8") == "KGENT_API_KEY=secret"


@pytest.mark.asyncio
async def test_todo_write_updates_session_state() -> None:
    store = TodoStateStore()
    tool = TodoWriteTool(session_id="sess_todo", state_store=store)

    result = await tool.call(
        {
            "items": [
                {"id": "a", "text": "read code", "status": "completed"},
                {"id": "b", "text": "write tests", "status": "in_progress"},
            ]
        }
    )

    assert "[x] a: read code" in result
    assert "[>] b: write tests" in result
    assert store.get_state("sess_todo").items[1].status == "in_progress"


@pytest.mark.asyncio
async def test_todo_write_rejects_duplicate_ids_without_mutation() -> None:
    store = TodoStateStore()
    tool = TodoWriteTool(session_id="sess_todo", state_store=store)
    await tool.call({"items": [{"id": "a", "text": "existing", "status": "pending"}]})

    with pytest.raises(ValueError):
        await tool.call(
            {
                "items": [
                    {"id": "a", "text": "one", "status": "pending"},
                    {"id": "a", "text": "two", "status": "pending"},
                ]
            }
        )

    assert [item.text for item in store.get_state("sess_todo").items] == ["existing"]


def test_registry_includes_mutation_tools_without_schema_risk_level(tmp_path: Path) -> None:
    tools = build_tools(tmp_path)

    write_tool = find_tool_by_name(tools, "write_file")
    edit_tool = find_tool_by_name(tools, "edit_file")

    assert write_tool is not None
    assert edit_tool is not None
    assert write_tool.risk_level == "high"
    assert edit_tool.risk_level == "high"
    assert "risk_level" not in tool_to_schema(write_tool)
    assert "risk_level" not in tool_to_schema(edit_tool)
