"""Tests for GrepTool."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.grep import GrepTool


@pytest.mark.asyncio
async def test_basic_text_match(tmp_path: Path) -> None:
    (tmp_path / "hello.py").write_text("def foo():\n    return 42\n")
    tool = GrepTool(project_root=tmp_path)
    result = await tool.call({"pattern": "return"})
    assert "hello.py" in result
    assert "return 42" in result


@pytest.mark.asyncio
async def test_regex_match(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("class Foo:\n    pass\nclass Bar:\n    pass\n")
    tool = GrepTool(project_root=tmp_path)
    result = await tool.call({"pattern": r"class \w+"})
    assert "class Foo" in result
    assert "class Bar" in result


@pytest.mark.asyncio
async def test_glob_filter(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("hello world\n")
    (tmp_path / "b.txt").write_text("hello world\n")
    tool = GrepTool(project_root=tmp_path)
    result = await tool.call({"pattern": "hello", "glob": "*.py"})
    assert "a.py" in result
    assert "b.txt" not in result


@pytest.mark.asyncio
async def test_max_results(tmp_path: Path) -> None:
    for i in range(10):
        (tmp_path / f"f{i}.py").write_text("match line\n")
    tool = GrepTool(project_root=tmp_path)
    result = await tool.call({"pattern": "match", "max_results": 3})
    lines = result.strip().splitlines()
    assert len(lines) == 3


@pytest.mark.asyncio
async def test_no_matches(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("nothing here\n")
    tool = GrepTool(project_root=tmp_path)
    result = await tool.call({"pattern": "zzzzz"})
    assert result == "<no matches>"


@pytest.mark.asyncio
async def test_path_safety(tmp_path: Path) -> None:
    tool = GrepTool(project_root=tmp_path)
    with pytest.raises(ValueError):
        await tool.call({"pattern": "x", "path": "../../etc"})


@pytest.mark.asyncio
async def test_search_subdirectory(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.py").write_text("found_it\n")
    tool = GrepTool(project_root=tmp_path)
    result = await tool.call({"pattern": "found_it", "path": "sub"})
    assert "deep.py" in result
