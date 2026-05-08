"""Concrete LLM provider implementations"""

from typing import Iterator, Optional

from ..exceptions import LLMError
from .base import LLMProvider
from .models import LLMResponse, LLMChunk


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible LLM provider"""

    def __init__(self, api_key: Optional[str], base_url: str, timeout: int = 60):
        from openai import OpenAI

        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        # Reuse one client instance to preserve connection pooling and timeout settings.
        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
    ) -> LLMResponse:
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            completion = self._client.chat.completions.create(**kwargs)
            choice = completion.choices[0]
            msg = choice.message

            return LLMResponse(
                content=msg.content or "",
                tool_calls=[
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in (msg.tool_calls or [])
                ],
                usage={
                    "prompt": completion.usage.prompt_tokens,
                    "completion": completion.usage.completion_tokens,
                    "total": completion.usage.total_tokens,
                }
                if completion.usage
                else None,
            )
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(
                user_message="LLM 调用失败，请检查 API Key 和网络连接",
                debug_message=f"{type(e).__name__}: {e}",
            ) from e

    def chat_stream(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
    ) -> Iterator[LLMChunk]:
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LLMChunk(
                        delta=chunk.choices[0].delta.content,
                        usage={
                            "prompt": chunk.usage.prompt_tokens,
                            "completion": chunk.usage.completion_tokens,
                            "total": chunk.usage.total_tokens,
                        }
                        if chunk.usage
                        else None,
                    )
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(
                user_message="LLM 流式调用失败，请检查 API Key 和网络连接",
                debug_message=f"{type(e).__name__}: {e}",
            ) from e


class ZhipuProvider(OpenAIProvider):
    """Zhipu (智谱 BigModel) LLM provider — OpenAI-compatible"""


class ModelScopeProvider(OpenAIProvider):
    """ModelScope LLM provider — OpenAI-compatible"""
