"""Tests for BashTool."""

from __future__ import annotations

import pytest

from app.tools.bash import BashTool


@pytest.mark.asyncio
async def test_simple_command() -> None:
    tool = BashTool()
    result = await tool.call({"command": "echo hello"})
    assert "hello" in result


@pytest.mark.asyncio
async def test_exit_code_nonzero() -> None:
    tool = BashTool()
    result = await tool.call({"command": "python -c 'import sys; sys.exit(1)'"})
    assert "exit code: 1" in result


@pytest.mark.asyncio
async def test_stderr_capture() -> None:
    tool = BashTool()
    result = await tool.call({"command": "python -c \"import sys; sys.stderr.write('err_out\\n')\""})
    assert "err_out" in result


@pytest.mark.asyncio
async def test_timeout() -> None:
    tool = BashTool()
    result = await tool.call({"command": "python -c \"import time; time.sleep(5)\"", "timeout": 1})
    assert "timeout" in result.lower()


@pytest.mark.asyncio
async def test_empty_output() -> None:
    tool = BashTool()
    result = await tool.call({"command": "python -c 'pass'"})
    assert result == "<no output>" or result == ""
