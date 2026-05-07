"""LLM provider abstraction and registry"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional

from .models import LLMResponse, LLMChunk


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
    ) -> LLMResponse:
        ...

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict],
        model: str,
        temperature: float,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
    ) -> Iterator[LLMChunk]:
        ...


class LLMProviderRegistry:
    """Registry for LLM providers"""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def register(self, name: str, provider: LLMProvider) -> None:
        if not isinstance(provider, LLMProvider):
            raise TypeError(
                f"Expected LLMProvider instance, got {type(provider).__name__}"
            )
        self._providers[name] = provider

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            available = ", ".join(self._providers.keys()) or "(none)"
            raise ValueError(
                f"LLM provider '{name}' not registered. Available: {available}"
            )
        return self._providers[name]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())
