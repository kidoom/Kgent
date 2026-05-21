"""Deterministic fake model client for pytest only (not a production provider)."""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.model.base import register_model_client
from app.runtime.messages import Message, ModelResponse, ToolResultBlock, ToolUseBlock
from app.runtime.prompts import PLAN_TURN_USER_PROMPT


@register_model_client("fake")
class FakeModelClient:
    """Offline stand-in so unit tests do not call DeepSeek."""

    def __init__(self, **_extra: Any):
        pass

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        if not tools:
            return self._plan_only(messages)
        return self._act(messages)

    def _plan_only(self, messages: list[Message]) -> ModelResponse:
        context = _messages_without_trailing_plan_prompt(messages)
        last = context[-1] if context else messages[-1]
        if isinstance(last.content, list) and last.content and isinstance(last.content[0], ToolResultBlock):
            tool_name = _find_tool_name_for_result(messages, last.content[0].tool_use_id) or "tool"
            if last.content[0].is_error:
                text = f"工具 {tool_name} 返回了错误，我将在下一步修正输入、换工具或向用户说明阻碍。"
            else:
                text = f"已收到 {tool_name} 的观察结果，我将据此决定继续调用工具还是给出最终答复。"
            return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

        user_text = _latest_user_text(context)
        recall_answer = self._answer_from_session_memory(context, user_text)
        if recall_answer is not None:
            text = "根据会话中的先前信息，我将在下一步直接回答用户，不再调用工具。"
            return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

        tool_use = self._maybe_plan_tool(user_text)
        if tool_use is None:
            text = "用户请求不需要外部工具，我将在下一步直接作答。"
        else:
            text = f"下一步我打算调用 {tool_use.name} 获取外部信息，然后再整理答复。"
        return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

    def _act(self, messages: list[Message]) -> ModelResponse:
        pending = _pending_tool_result(messages)
        if pending is not None:
            return self._answer_from_tool_result(messages, pending)

        user_text = _latest_user_text(messages)
        recall_answer = self._answer_from_session_memory(messages, user_text)
        if recall_answer is not None:
            return ModelResponse(
                assistant_message=Message(role="assistant", content=recall_answer),
                text=recall_answer,
            )

        tool_use = self._maybe_plan_tool(user_text)
        if tool_use is None:
            text = "我是 Kgent，一个最小版 tool-using agent。当前请求不需要工具，我可以直接回答。"
            return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text)

        plan = f"我将调用 {tool_use.name} 来完成这一步。"
        return ModelResponse(
            assistant_message=Message(
                role="assistant",
                content=[tool_use],
                assistant_text=plan,
            ),
            text=plan,
            tool_uses=[tool_use],
        )

    def _answer_from_session_memory(self, messages: list[Message], user_text: str) -> str | None:
        if _is_name_recall_question(user_text):
            name = _extract_introduced_name(messages)
            if name:
                return f"你叫{name}。"

        if _is_prior_context_question(user_text):
            preview = _latest_read_file_content(messages)
            if preview:
                if len(preview) > 400:
                    preview = preview[:400] + "..."
                return f"根据上一轮读取的文件内容，这个项目主要是：\n\n{preview}"

        return None

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


def _is_name_recall_question(text: str) -> bool:
    return any(phrase in text for phrase in ["我叫什么", "我的名字", "我是谁"])


def _extract_introduced_name(messages: list[Message]) -> str | None:
    for message in messages:
        if message.role == "user" and isinstance(message.content, str):
            match = re.search(r"我叫\s*([^\s，,。.!！?？]+)", message.content)
            if match:
                return match.group(1).strip()
    return None


def _is_prior_context_question(text: str) -> bool:
    return any(
        phrase in text
        for phrase in ["刚才", "刚刚", "之前", "上一轮", "那个项目", "读的内容", "读到的"]
    )


def _latest_read_file_content(messages: list[Message]) -> str | None:
    for message in reversed(messages):
        if message.role == "user" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolResultBlock) and not block.is_error:
                    tool_name = _find_tool_name_for_result(messages, block.tool_use_id)
                    if tool_name == "read_file":
                        return block.content
    return None


def _messages_without_trailing_plan_prompt(messages: list[Message]) -> list[Message]:
    if (
        messages
        and messages[-1].role == "user"
        and isinstance(messages[-1].content, str)
        and messages[-1].content == PLAN_TURN_USER_PROMPT
    ):
        return messages[:-1]
    return messages


def _latest_user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "user" and isinstance(message.content, str):
            if message.content == PLAN_TURN_USER_PROMPT:
                continue
            return message.content
    return ""


def _extract_expression(text: str) -> str | None:
    matches = re.findall(r"[0-9][0-9\s+\-*/().%]*[0-9]", text)
    candidates = [match.strip() for match in matches if any(op in match for op in ["+", "-", "*", "/", "%"])]
    return max(candidates, key=len) if candidates else None


def _extract_file_path(text: str) -> str | None:
    match = re.search(r"([A-Za-z0-9_.\-/]+\.(?:md|txt|json|yaml|yml|py))", text)
    return match.group(1) if match else None


def _pending_tool_result(messages: list[Message]) -> ToolResultBlock | None:
    last_index = -1
    last_block: ToolResultBlock | None = None
    for index, message in enumerate(messages):
        if message.role != "user" or not isinstance(message.content, list):
            continue
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                last_index = index
                last_block = block
    if last_block is None:
        return None
    for message in messages[last_index + 1 :]:
        if message.role == "user" and isinstance(message.content, str):
            return None
        if message.role == "assistant" and isinstance(message.content, list):
            return None
    return last_block


def _find_tool_name_for_result(messages: list[Message], tool_use_id: str) -> str | None:
    for message in reversed(messages):
        if message.role == "assistant" and isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.id == tool_use_id:
                    return block.name
    return None


def _tool_use_id() -> str:
    return f"toolu_{uuid.uuid4().hex[:8]}"
