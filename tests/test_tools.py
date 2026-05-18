from pathlib import Path

import pytest

from app.tools.calculator import CalculatorTool
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
