from pathlib import Path

import pytest

from app.runtime.loop import run_agent
from fake_model import FakeModelClient
from app.tools.registry import build_tools


@pytest.mark.asyncio
async def test_same_session_remembers_name() -> None:
    client = FakeModelClient()
    tools = build_tools(Path.cwd())

    first = await run_agent("我叫小明", model_client=client, tools=tools, session_id="s1")
    second = await run_agent("我叫什么？", model_client=client, tools=tools, session_id="s1")

    assert "小明" in second.answer
    assert second.message_count > first.message_count


@pytest.mark.asyncio
async def test_different_sessions_are_isolated() -> None:
    client = FakeModelClient()
    tools = build_tools(Path.cwd())

    await run_agent("我喜欢 Python", model_client=client, tools=tools, session_id="s1")
    second = await run_agent("我喜欢什么语言？", model_client=client, tools=tools, session_id="s2")

    assert "Python" not in second.answer


@pytest.mark.asyncio
async def test_tool_results_persist_in_session(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nA tiny agent project.", encoding="utf-8")
    client = FakeModelClient()
    tools = build_tools(tmp_path)

    await run_agent(
        "请读取 README.md 并总结这个项目",
        model_client=client,
        tools=tools,
        session_id="s1",
    )
    second = await run_agent(
        "刚才那个项目主要是干什么的？",
        model_client=client,
        tools=tools,
        session_id="s1",
    )

    assert "Demo" in second.answer or "tiny agent" in second.answer


@pytest.mark.asyncio
async def test_remembers_read_file_after_刚刚(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nA tiny agent project.", encoding="utf-8")
    client = FakeModelClient()
    tools = build_tools(tmp_path)

    await run_agent(
        "请读取 README.md 并总结这个项目",
        model_client=client,
        tools=tools,
        session_id="s1",
    )
    second = await run_agent(
        "总结一下刚刚读的内容",
        model_client=client,
        tools=tools,
        session_id="s1",
    )

    assert "Demo" in second.answer or "tiny agent" in second.answer


@pytest.mark.asyncio
async def test_new_user_message_does_not_reconsume_old_tool_result(tmp_path: Path) -> None:
    client = FakeModelClient()
    tools = build_tools(tmp_path)
    session_id = "s_tool_result_consumed"

    first = await run_agent(
        "calculate 12 * 8 + 6",
        model_client=client,
        tools=tools,
        session_id=session_id,
    )
    second = await run_agent(
        "hello, who are you?",
        model_client=client,
        tools=tools,
        session_id=session_id,
    )

    assert "102" in first.answer
    assert second.answer != first.answer
    assert "102" not in second.answer
