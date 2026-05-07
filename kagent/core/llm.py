"""LLM module: LLM Provider abstraction and registry"""

from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Response from LLM provider"""

    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    usage: Optional[dict] = None  # {"prompt": int, "completion": int, "total": int}
    raw: Any = None  # Provider raw response, not logged by default


class LLMChunk(BaseModel):
    """Streaming chunk from LLM provider"""

    delta: str
    usage: Optional[dict] = None
    raw: Any = None


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
        """Send a chat request to the LLM provider.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model ID to use.
            temperature: Sampling temperature.
            tools: Optional list of tool definitions.
            tool_choice: Optional tool choice directive.

        Returns:
            LLMResponse with the model's response.
        """
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
        
        """Send a streaming chat request to the LLM provider.
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model ID to use.
            temperature: Sampling temperature.
            tools: Optional list of tool definitions.
            tool_choice: Optional tool choice directive.

        Yields:
            LLMChunk objects as they arrive.
        """
        ...


class LLMProviderRegistry:
    """Registry for LLM providers"""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def register(self, name: str, provider: LLMProvider) -> None:
        """Register an LLM provider.

        Args:
            name: Provider name (e.g., 'openai', 'ollama').
            provider: LLMProvider instance.

        Raises:
            TypeError: If provider is not an LLMProvider instance.
        """
        if not isinstance(provider, LLMProvider):
            raise TypeError(
                f"Expected LLMProvider instance, got {type(provider).__name__}"
            )
        self._providers[name] = provider

    def get(self, name: str) -> LLMProvider:
        """Get a registered LLM provider.

        Args:
            name: Provider name.

        Returns:
            LLMProvider instance.

        Raises:
            ValueError: If provider is not registered.
        """
        if name not in self._providers:
            available = ", ".join(self._providers.keys()) or "(none)"
            raise ValueError(
                f"LLM provider '{name}' not registered. Available: {available}"
            )
        return self._providers[name]

    def list_providers(self) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names.
        """
        return list(self._providers.keys())
