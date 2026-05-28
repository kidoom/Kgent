"""OpenAI-compatible chat completions client.

Works with any OpenAI-compatible API (OpenAI, DeepSeek, etc.) via base_url.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

import httpx

from app.runtime.messages import Message, ModelResponse, TokenUsage, ToolResultBlock, ToolUseBlock
from app.model.base import ModelClientError, PromptTooLongError, register_model_client


def _should_bypass_proxy(base_url: str) -> bool:
    """Check if the base_url host is in NO_PROXY list."""
    no_proxy = os.environ.get("NO_PROXY", os.environ.get("no_proxy", ""))
    if not no_proxy or not base_url:
        return False
    host = urlparse(base_url).hostname or ""
    if not host:
        return False
    no_proxy_list = [h.strip().lower() for h in no_proxy.split(",") if h.strip()]
    return host.lower() in no_proxy_list


@register_model_client("openai")
class OpenAIModelClient:
    """OpenAI-compatible chat completions client."""

    def __init__(self, model: str = "gpt-4.1-mini", api_key: str = "", base_url: str = "", **_extra: Any):
        from openai import AsyncOpenAI

        self.model = model
        
        # If base_url is in NO_PROXY list, create httpx client without proxy
        if _should_bypass_proxy(base_url):
            http_client = httpx.AsyncClient(proxy=None)
            self._client = AsyncOpenAI(
                api_key=api_key or None,
                base_url=base_url or None,
                http_client=http_client,
            )
        else:
            self._client = AsyncOpenAI(api_key=api_key or None, base_url=base_url or None)

    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": _to_openai_messages(messages),
        }
        if tools:
            request["tools"] = [_to_openai_tool(tool) for tool in tools]
            request["tool_choice"] = "auto"
        try:
            response = await self._client.chat.completions.create(**request)
        except Exception as exc:
            msg = str(exc).lower()
            if any(
                phrase in msg
                for phrase in (
                    "context_length_exceeded",
                    "prompt too long",
                    "maximum context length",
                    "maximum token",
                    "too many tokens",
                    "413",
                )
            ):
                raise PromptTooLongError(f"Prompt exceeds context window: {exc}") from exc
            raise ModelClientError(f"Model API call failed: {exc}") from exc

        choice = response.choices[0].message
        usage = _parse_usage(response)
        tool_calls = choice.tool_calls or []
        if tool_calls:
            tool_uses = []
            for call in tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError as exc:
                    raise ModelClientError(
                        f"Model returned invalid JSON in tool arguments: {call.function.arguments}"
                    ) from exc
                tool_uses.append(
                    ToolUseBlock(
                        id=call.id,
                        name=call.function.name,
                        input=args,
                    )
                )
            text = (choice.content or "").strip()
            return ModelResponse(
                assistant_message=Message(
                    role="assistant",
                    content=tool_uses,
                    assistant_text=text or None,
                ),
                text=text,
                tool_uses=tool_uses,
                usage=usage,
            )

        text = choice.content or ""
        return ModelResponse(assistant_message=Message(role="assistant", content=text), text=text, usage=usage)

    async def close(self) -> None:
        """Close the underlying HTTP client to avoid event loop warnings."""
        await self._client.close()


# ---------------------------------------------------------------------------
# OpenAI message format conversion
# ---------------------------------------------------------------------------

def _to_openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message.content, str):
            converted.append({"role": message.role, "content": message.content})
            continue
        if message.role == "assistant":
            converted.append({
                "role": "assistant",
                "content": message.assistant_text or None,
                "tool_calls": [
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input, ensure_ascii=False),
                        },
                    }
                    for block in message.content
                    if isinstance(block, ToolUseBlock)
                ],
            })
            continue
        if message.role == "tool":
            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    converted.append({"role": "tool", "tool_call_id": block.tool_use_id, "content": block.content})
    return converted


def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _parse_usage(response: Any) -> TokenUsage | None:
    """Extract token usage from an OpenAI-compatible response."""
    raw = getattr(response, "usage", None)
    if raw is None:
        return None
    return TokenUsage(
        prompt_tokens=getattr(raw, "prompt_tokens", None),
        completion_tokens=getattr(raw, "completion_tokens", None),
        total_tokens=getattr(raw, "total_tokens", None),
    )
