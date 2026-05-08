"""AgentLLM facade: configuration-driven LLM provider selection"""

import importlib
from typing import Iterator, Optional

from ..config import Config
from ..exceptions import ConfigError
from .base import LLMProvider, LLMProviderRegistry
from .models import LLMResponse, LLMChunk


PROVIDER_CONFIG: dict[str, dict] = {
    "openai": {
        "class": "kagent.core.llm.providers.OpenAIProvider",
        "default_base_url": "https://api.openai.com/v1",
        "requires_api_key": True,
    },
    "ollama": {
        "class": "kagent.core.llm.providers.OpenAIProvider",
        "default_base_url": "http://localhost:11434/v1",
        "requires_api_key": False,
    },
    "vllm": {
        "class": "kagent.core.llm.providers.OpenAIProvider",
        "default_base_url": "http://localhost:8000/v1",
        "requires_api_key": False,
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
        self.timeout = timeout if timeout is not None else cfg.timeout

        if not self.base_url:
            pcfg = PROVIDER_CONFIG.get(self.provider_name, {})
            self.base_url = pcfg.get("default_base_url")

        self._provider = self._get_or_load_provider()

    def _get_or_load_provider(self) -> LLMProvider:
        try:
            return self._registry.get(self.provider_name)
        except ValueError:
            cfg = PROVIDER_CONFIG.get(self.provider_name)
            if not cfg:
                raise ConfigError(
                    f"LLM provider '{self.provider_name}' is not registered and has no "
                    f"known lazy-load config. Available providers: {self._registry.list_providers()}."
                )

            if cfg.get("requires_api_key", True) and not self.api_key:
                raise ConfigError(
                    f"LLM_API_KEY is required for provider '{self.provider_name}'."
                )

            class_path = cfg.get("class")
            if not class_path:
                raise ConfigError(
                    f"Provider '{self.provider_name}' is not registered and has invalid "
                    "PROVIDER_CONFIG (missing 'class')."
                )

            try:
                module_name, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                provider_cls = getattr(module, class_name)
            except (ValueError, ImportError, AttributeError) as e:
                raise ConfigError(
                    f"Failed to lazy-load provider '{self.provider_name}' from "
                    f"'{class_path}': {e}"
                ) from e

            provider = provider_cls(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
            self._registry.register(self.provider_name, provider)
            return provider

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
