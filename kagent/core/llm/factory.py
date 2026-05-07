"""AgentLLM facade: configuration-driven LLM provider selection"""

from typing import Iterator, Optional

from ..config import Config
from ..exceptions import ConfigError
from .base import LLMProvider, LLMProviderRegistry
from .models import LLMResponse, LLMChunk


PROVIDER_CONFIG: dict[str, dict] = {
    "openai": {
        "default_base_url": "https://api.openai.com/v1",
        "env_key": "LLM_API_KEY",
        "env_base_url": "LLM_BASE_URL",
    },
    "ollama": {
        "default_base_url": "http://localhost:11434/v1",
        "env_key": None,
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
        cfg = config or Config.from_env()

        self.provider_name = provider or cfg.default_provider
        self.model = model or cfg.default_model
        self.api_key = api_key or cfg.api_key
        self.base_url = base_url or cfg.base_url
        self.timeout = timeout

        if not self.base_url:
            pcfg = PROVIDER_CONFIG.get(self.provider_name, {})
            self.base_url = pcfg.get("default_base_url")

        self._provider = self._get_provider()

    def _get_provider(self) -> LLMProvider:
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
        yield from self._provider.chat_stream(
            messages=messages,
            model=self.model,
            temperature=temperature if temperature is not None else 0.0,
            tools=tools,
            tool_choice=tool_choice,
        )
