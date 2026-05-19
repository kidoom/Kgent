from pathlib import Path

import pytest

from app.tools.calculator import CalculatorTool
from app.tools.list_files import ListFilesTool
from app.tools.read_file import ReadFileTool


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
