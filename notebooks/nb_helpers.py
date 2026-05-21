"""Helpers for the Kgent agent-loop Jupyter walkthrough."""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CHECKPOINT_TITLES: dict[str, str] = {
    "after_user_append": "0 · 用户消息写入 session",
    "turn_begin": "Loop · turn 开始",
    "before_plan_call": "Plan · call_model（无 tools，仅 debug CLI）",
    "after_plan": "Plan · 计划文本写入 session",
    "before_model_call": "call_model · 请求 LLM（messages + tools[]）",
    "after_model": "call_model · 模型响应写入 session",
    "after_think_placeholder": "占位 think（模型只返回 tool_calls、无可见文本）",
    "after_act": "Act · 模型响应（plan_before_act 路径）",
    "after_permission": "权限决策后",
    "after_tool": "工具执行 · tool_result 写入 session",
    "complete": "本轮结束 · 最终答案",
}


def setup_python_path() -> Path:
    """Add repo backend/ to sys.path; return repo root."""
    repo_root = Path(__file__).resolve().parents[1]
    backend = repo_root / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    return repo_root


def preview_openai_request(
    messages_payload: list[dict[str, Any]],
    tool_schemas: list[dict[str, Any]],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """Show the HTTP body shape sent to OpenAI-compatible APIs (DeepSeek)."""
    from app.model.openai import _to_openai_messages, _to_openai_tool
    from app.runtime.messages import Message

    messages = [Message.model_validate(item) for item in messages_payload]
    body: dict[str, Any] = {
        "model": model or "<from KGENT_MODEL>",
        "messages": _to_openai_messages(messages),
    }
    if tool_schemas:
        body["tools"] = [_to_openai_tool(schema) for schema in tool_schemas]
        body["tool_choice"] = "auto"
    return body


def ensure_deepseek_ready() -> Any:
    """Load .env and verify DeepSeek (OpenAI-compatible) configuration."""
    from app.core.config import get_dotenv_settings, mask_secret, reload_dotenv_settings

    reload_dotenv_settings()
    settings = get_dotenv_settings()

    if settings.provider != "openai":
        raise RuntimeError(
            "Notebook 需要 DeepSeek：请在项目根 .env 设置 "
            "KGENT_PROVIDER=openai, KGENT_BASE_URL=https://api.deepseek.com"
        )
    if not settings.api_key:
        raise RuntimeError(
            "KGENT_API_KEY 为空。请在 D:\\Kgent\\.env 填入 DeepSeek API Key。"
        )
    if "deepseek" not in settings.base_url.lower():
        print(f"[warn] base_url 不是 DeepSeek 默认地址: {settings.base_url}")

    print("DeepSeek 配置 OK")
    print("  provider:", settings.provider)
    print("  model:", settings.model)
    print("  base_url:", settings.base_url)
    print("  api_key:", mask_secret(settings.api_key))
    return settings


def _display_markdown(text: str) -> None:
    from IPython.display import Markdown, display

    display(Markdown(text))


def _display_json(obj: Any) -> None:
    from IPython.display import display

    display(json.dumps(obj, ensure_ascii=False, indent=2))


def messages_markdown(messages: list[dict[str, Any]], *, show_system_full: bool = False) -> str:
    lines = ["| # | role | content |", "|---:|---|---|"]
    for index, message in enumerate(messages):
        role = message.get("role", "?")
        content = message.get("content", "")
        if role == "system" and not show_system_full and isinstance(content, str):
            preview = content[:80].replace("\n", " ")
            cell = f"*(system, {len(content)} chars)* `{preview}...`"
        elif isinstance(content, str):
            cell = f"`{content[:200]}{'...' if len(content) > 200 else ''}`"
        elif isinstance(content, list):
            parts: list[str] = []
            if message.get("assistant_text"):
                parts.append(f"plan: {message['assistant_text'][:80]}")
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    parts.append(
                        f"**tool_use** `{block.get('name')}` "
                        f"input={json.dumps(block.get('input', {}), ensure_ascii=False)}"
                    )
                elif block.get("type") == "tool_result":
                    flag = " ERROR" if block.get("is_error") else ""
                    parts.append(
                        f"**tool_result{flag}** → `{str(block.get('content', ''))[:120]}`"
                    )
            cell = "<br>".join(parts) if parts else json.dumps(content, ensure_ascii=False)
        else:
            cell = json.dumps(content, ensure_ascii=False)
        lines.append(f"| {index} | `{role}` | {cell} |")
    return "\n".join(lines)


def steps_markdown(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return "*(本 checkpoint 无新增 step)*"
    lines = ["| type | turn | detail |", "|---|---:|---|"]
    for step in steps:
        detail = step.get("content") or ""
        if step.get("type") == "call":
            detail = f"`{step.get('tool_name')}` {json.dumps(step.get('tool_input', {}), ensure_ascii=False)}"
        elif step.get("type") == "observe":
            detail = f"`{step.get('tool_name')}` → {step.get('content', '')[:100]}"
        lines.append(f"| `{step.get('type')}` | {step.get('turn_index')} | {detail} |")
    return "\n".join(lines)


def display_checkpoint(event: Any, *, index: int, model: str | None = None) -> None:
    payload = event.payload
    checkpoint = payload.get("checkpoint", "?")
    turn = payload.get("turn_index", -1)
    title = CHECKPOINT_TITLES.get(checkpoint, checkpoint)
    _display_markdown(f"### [{index}] {title} `(turn={turn})`")

    if checkpoint == "before_model_call":
        tool_schemas = payload.get("tool_schemas") or []
        messages = payload.get("messages") or []
        _display_markdown("**发给 LLM 的请求体预览（OpenAI 格式）**")
        _display_json(preview_openai_request(messages, tool_schemas, model=model))

    _display_markdown("**session messages 快照**")
    _display_markdown(messages_markdown(payload.get("messages") or []))

    added = payload.get("added_steps") or []
    if added:
        _display_markdown("**本阶段新增 agent steps**")
        _display_markdown(steps_markdown(added))


@dataclass
class WalkthroughRun:
    user_input: str
    provider: str
    model: str = ""
    events: list[Any] = field(default_factory=list)
    answer: str = ""
    message_count: int = 0

    @property
    def checkpoints(self) -> list[Any]:
        return [event for event in self.events if event.type == "loop_checkpoint"]


async def run_walkthrough(
    user_input: str,
    *,
    session_id: str = "notebook-demo",
    provider: str | None = "openai",
    plan_before_act: bool = False,
    reset_session: bool = True,
) -> WalkthroughRun:
    """Run one user turn and collect all loop_checkpoint events."""
    from app.core.config import get_dotenv_settings, reload_dotenv_settings
    from app.memory.session_store import reset_sessions
    from app.model_client import ModelClientError, build_model_client
    from app.runtime.host import CollectingHost
    from app.runtime.loop import run_agent_stream
    from app.runtime.permissions import AllowAllPolicy
    from app.tools.registry import build_tools

    reload_dotenv_settings()
    settings = get_dotenv_settings()
    chosen = provider or settings.provider

    if chosen == "openai" and not settings.api_key:
        raise RuntimeError("DeepSeek 需要 KGENT_API_KEY，请检查 .env")

    if reset_session:
        reset_sessions()

    try:
        model_client = build_model_client(chosen, **settings.model_kwargs)
    except ModelClientError as exc:
        raise RuntimeError(f"无法创建 model client: {exc}") from exc
    tools = build_tools(settings.project_root)
    run_id = f"nb_{uuid.uuid4().hex[:8]}"
    host = CollectingHost(
        run_id=run_id,
        session_id=session_id,
        auto_resolve_ask=True,
    )

    try:
        await run_agent_stream(
            run_id=run_id,
            session_id=session_id,
            message=user_input,
            model_client=model_client,
            tools=tools,
            host=host,
            policy=AllowAllPolicy(),
            max_steps=settings.max_steps,
            max_session_messages=settings.max_session_messages,
            plan_before_act=plan_before_act,
        )
    finally:
        close = getattr(model_client, "close", None)
        if close is not None:
            await close()

    result = host.to_agent_result()
    return WalkthroughRun(
        user_input=user_input,
        provider=chosen,
        model=settings.model,
        events=list(host.events),
        answer=result.answer,
        message_count=result.message_count,
    )


def show_tool_registry() -> None:
    from app.core.config import get_dotenv_settings
    from app.tools.registry import build_tool_schemas, build_tools

    settings = get_dotenv_settings()
    tools = build_tools(settings.project_root)
    schemas = build_tool_schemas(tools)

    _display_markdown("## 注册的工具（Python 实例 → tool_schemas）")
    for tool, schema in zip(tools, schemas):
        _display_markdown(f"### `{tool.name}` · risk=`{getattr(tool, 'risk_level', '?')}`")
        _display_markdown(tool.description)
        _display_json(schema)
