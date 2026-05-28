"""Tests for git read-only tools."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.tools.git_diff import GitDiffTool
from app.tools.git_log import GitLogTool
from app.tools.git_status import GitStatusTool


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)


@pytest.mark.asyncio
async def test_git_status_clean(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    tool = GitStatusTool(project_root=tmp_path)
    result = await tool.call({})
    assert "working tree clean" in result


@pytest.mark.asyncio
async def test_git_status_dirty(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "new.txt").write_text("untracked")
    tool = GitStatusTool(project_root=tmp_path)
    result = await tool.call({})
    assert "new.txt" in result


@pytest.mark.asyncio
async def test_git_diff_no_changes(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True, check=True)
    tool = GitDiffTool(project_root=tmp_path)
    result = await tool.call({})
    assert "<no changes>" in result


@pytest.mark.asyncio
async def test_git_diff_unstaged(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    f = tmp_path / "file.txt"
    f.write_text("original")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "add"], cwd=tmp_path, capture_output=True, check=True)
    f.write_text("modified")
    tool = GitDiffTool(project_root=tmp_path)
    result = await tool.call({})
    assert "modified" in result


@pytest.mark.asyncio
async def test_git_log(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "a.txt").write_text("a")
    subprocess.run(["git", "add", "a.txt"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "first commit"], cwd=tmp_path, capture_output=True, check=True)
    tool = GitLogTool(project_root=tmp_path)
    result = await tool.call({})
    assert "first commit" in result


@pytest.mark.asyncio
async def test_git_log_custom_count(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    for i in range(3):
        (tmp_path / f"f{i}.txt").write_text(str(i))
        subprocess.run(["git", "add", f"f{i}.txt"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", f"commit {i}"], cwd=tmp_path, capture_output=True, check=True)
    tool = GitLogTool(project_root=tmp_path)
    result = await tool.call({"count": 2})
    lines = result.strip().splitlines()
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_git_status_not_a_repo(tmp_path: Path) -> None:
    tool = GitStatusTool(project_root=tmp_path)
    result = await tool.call({})
    assert "git error" in result.lower() or "not" in result.lower()
