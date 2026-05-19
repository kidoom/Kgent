from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agent.loop import run_agent
from app.agent.model_client import HeuristicModelClient
from app.core.config import reload_settings
from app.main import app
from app.tools.registry import build_tools


@pytest.mark.asyncio
async def test_same_session_remembers_name() -> None:
    client = HeuristicModelClient()
    tools = build_tools(Path.cwd())

    first = await run_agent("我叫小明", model_client=client, tools=tools, session_id="s1")
    second = await run_agent("我叫什么？", model_client=client, tools=tools, session_id="s1")

    assert "小明" in second.answer
    assert second.message_count > first.message_count


@pytest.mark.asyncio
async def test_different_sessions_are_isolated() -> None:
    client = HeuristicModelClient()
    tools = build_tools(Path.cwd())

    await run_agent("我喜欢 Python", model_client=client, tools=tools, session_id="s1")
    second = await run_agent("我喜欢什么语言？", model_client=client, tools=tools, session_id="s2")

    assert "Python" not in second.answer


@pytest.mark.asyncio
async def test_tool_results_persist_in_session(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nA tiny agent project.", encoding="utf-8")
    client = HeuristicModelClient()
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


def test_chat_api_session_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KGENT_PROVIDER", "heuristic")
    monkeypatch.setenv("KGENT_PROJECT_ROOT", str(tmp_path))
    reload_settings()

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={"session_id": "api-s1", "message": "我叫小明"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "api-s1"
    assert data["message_count"] >= 3

    response2 = client.post(
        "/api/chat",
        json={"session_id": "api-s1", "message": "我叫什么？"},
    )
    assert response2.status_code == 200
    assert "小明" in response2.json()["answer"]
    assert response2.json()["message_count"] > data["message_count"]
