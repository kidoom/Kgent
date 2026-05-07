"""LLM module: LLM Provider abstraction and registry"""

from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field

from .config import Config, ConfigError


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


# Provider configuration
PROVIDER_CONFIG: dict[str, dict] = {
    "openai": {
        "default_base_url": "https://api.openai.com/v1",
        "env_key": "LLM_API_KEY",
        "env_base_url": "LLM_BASE_URL",
    },
    "ollama": {
        "default_base_url": "http://localhost:11434/v1",
        "env_key": None,  # Ollama doesn't need API key
        "env_base_url": "LLM_BASE_URL",
    },
    "vllm": {
        "default_base_url": "http://localhost:8000/v1",
        "env_key": None,
        "env_base_url": "LLM_BASE_URL",
    },
}


class AgentLLM:
    """Facade for LLM providers with configuration-driven selection"""

    _registry = LLMProviderRegistry()

    @classmethod
    def register_provider(cls, name: str, provider: LLMProvider) -> None:
        """Register a provider globally."""
        cls._registry.register(name, provider)

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        config: Optional[Config] = None,
    ):
        """Initialize AgentLLM with configuration.

        All values are resolved via Config, with explicit params as overrides.

        Args:
            provider: Provider name override.
            model: Model ID override.
            api_key: API key override.
            base_url: Base URL override.
            timeout: Request timeout in seconds.
            config: Config instance. If None, loaded from Config.from_env().
        """
        cfg = config or Config.from_env()

        self.provider_name = provider or cfg.default_provider
        self.model = model or cfg.default_model
        self.api_key = api_key or cfg.api_key
        self.base_url = base_url or cfg.base_url
        self.timeout = timeout

        # Resolve base_url default from provider config
        if not self.base_url:
            pcfg = PROVIDER_CONFIG.get(self.provider_name, {})
            self.base_url = pcfg.get("default_base_url")

        # Get provider instance
        self._provider = self._get_provider()

    def _get_provider(self) -> LLMProvider:
        """Get provider from registry or raise error.

        Returns:
            LLMProvider instance.

        Raises:
            ConfigError: If provider is not registered.
        """
        try:
            return self._registry.get(self.provider_name)
        except ValueError:
            raise ConfigError(
                f"LLM provider '{self.provider_name}' is not registered. "
                f"Available providers: {self._registry.list_providers()}. "
                f"Use AgentLLM.register_provider() to register a provider."
            )

    def invoke(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
        **kwargs,
    ) -> LLMResponse:
        """Send a non-streaming chat request.

        Args:
            messages: List of message dicts.
            temperature: Sampling temperature. If None, uses default (0.0).
            tools: Optional tool definitions.
            tool_choice: Optional tool choice directive.

        Returns:
            LLMResponse with the model's response.
        """
        return self._provider.chat(
            messages=messages,
            model=self.model,
            temperature=temperature if temperature is not None else 0.0,
            tools=tools,
            tool_choice=tool_choice,
        )

    def stream(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
        **kwargs,
    ) -> Iterator[LLMChunk]:
        """Send a streaming chat request.

        Args:
            messages: List of message dicts.
            temperature: Sampling temperature. If None, uses default (0.0).
            tools: Optional tool definitions.
            tool_choice: Optional tool choice directive.

        Yields:
            LLMChunk objects as they arrive.
        """
        yield from self._provider.chat_stream(
            messages=messages,
            model=self.model,
            temperature=temperature if temperature is not None else 0.0,
            tools=tools,
            tool_choice=tool_choice,
        )
