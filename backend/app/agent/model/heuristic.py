"""Deterministic local model client — no network, no API key."""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.agent.messages import Message, ModelResponse, ToolResultBlock, ToolUseBlock
from app.agent.model.base import register_model_client


@register_model_client("heuristic")
class HeuristicModelClient:
    """Small local stand-in for an LLM that can emit tool_use blocks.

    This is not meant to be smart. It exists so the agent loop can run and
    be tested without network access or API keys.
    """

    def __init__(self, **_extra: Any):
        pass

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        del tools
        last = messages[-1]
        if isinstance(last.content, list) and last.content and isinstance(last.content[0], ToolResultBlock):
            return self._answer_from_tool_result(messages, last.content[0])

        user_text = _latest_user_text(messages)
        tool_use = self._maybe_plan_tool(user_text)
        if tool_use is None:
            text = "我是 Kgent，一个最小版 tool-using agent。当前请求不需要工具，我可以直接回答。"
            return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

        return ModelResponse(
            assistant_message=Message(role="assistant", content=[tool_use]),
            tool_uses=[tool_use],
        )

    def _maybe_plan_tool(self, text: str) -> ToolUseBlock | None:
        expression = _extract_expression(text)
        if expression is not None:
            return ToolUseBlock(
                id=_tool_use_id(),
                name="calculator",
                input={"expression": expression},
            )

        file_path = _extract_file_path(text)
        if file_path is not None:
            return ToolUseBlock(
                id=_tool_use_id(),
                name="read_file",
                input={"path": file_path},
            )

        lowered = text.lower()
        if any(phrase in lowered for phrase in ["list files", "show files", "files"]):
            return ToolUseBlock(id=_tool_use_id(), name="list_files", input={"path": "."})
        if any(phrase in text for phrase in ["列出", "目录", "文件列表", "有哪些文件"]):
            return ToolUseBlock(id=_tool_use_id(), name="list_files", input={"path": "."})

        return None

    def _answer_from_tool_result(self, messages: list[Message], result: ToolResultBlock) -> ModelResponse:
        tool_name = _find_tool_name_for_result(messages, result.tool_use_id)
        if result.is_error:
            text = f"工具 {tool_name or result.tool_use_id} 执行失败：{result.content}"
        elif tool_name == "calculator":
            text = f"计算结果是 {result.content}。"
        elif tool_name == "read_file":
            preview = result.content.strip()
            if len(preview) > 800:
                preview = preview[:800] + "..."
            text = f"我读取到了文件内容。简要来看：\n\n{preview}"
        elif tool_name == "list_files":
            text = f"当前目录包含：\n\n{result.content}"
        else:
            text = result.content
        return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user" and isinstance(message.content, str):
            return message.content
    return ""


def _extract_expression(text: str) -> str | None:
    matches = re.findall(r"[0-9][0-9\s+\-*/().%]*[0-9]", text)
    candidates = [match.strip() for match in matches if any(op in match for op in ["+", "-", "*", "/", "%"])]
    return max(candidates, key=len) if candidates else None


def _extract_file_path(text: str) -> str | None:
    match = re.search(r"([A-Za-z0-9_.\-/]+\.(?:md|txt|json|yaml|yml|py))", text)
    return match.group(1) if match else None


def _find_tool_name_for_result(messages: list[Message], tool_use_id: str) -> str | None:
    for message in reversed(messages):
        if message.role == "assistant" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.id == tool_use_id:
                    return block.name
    return None


def _tool_use_id() -> str:
    return f"toolu_{uuid.uuid4().hex[:8]}"
