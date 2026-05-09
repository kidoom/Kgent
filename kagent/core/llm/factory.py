"""AgentLLM facade: configuration-driven LLM provider selection"""

import importlib
from typing import Iterator, Optional

from ..config import Config
from ..exceptions import ConfigError
from ..tracing import Tracer
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
    "zhipu": {
        "class": "kagent.core.llm.providers.ZhipuProvider",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "requires_api_key": True,
    },
    "modelscope": {
        "class": "kagent.core.llm.providers.ModelScopeProvider",
        "default_base_url": "https://api-inference.modelscope.cn/v1",
        "requires_api_key": True,
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

        if self.provider_name == "auto":
            self.provider_name = self._auto_detect(self.base_url)

        if not self.base_url:
            pcfg = PROVIDER_CONFIG.get(self.provider_name, {})
            self.base_url = pcfg.get("default_base_url")

        self._provider = self._get_or_load_provider()

    @staticmethod
    def _auto_detect(base_url: Optional[str] = None) -> str:
        """Heuristically detect provider from base_url."""
        if not base_url:
            return "openai"
        url = base_url.lower()
        if "localhost:11434" in url:
            return "ollama"
        if "bigmodel.cn" in url:
            return "zhipu"
        if "modelscope.cn" in url:
            return "modelscope"
        return "openai"

    def _get_or_load_provider(self) -> LLMProvider:
        try:
            return self._registry.get(self.provider_name)
        except ValueError:
            cfg = PROVIDER_CONFIG.get(self.provider_name)
            if not cfg:
                raise ConfigError(
                    user_message=f"LLM provider '{self.provider_name}' is not registered and has no "
                    f"known lazy-load config. Available providers: {self._registry.list_providers()}.",
                    debug_message=f"provider={self.provider_name}, PROVIDER_CONFIG keys={list(PROVIDER_CONFIG.keys())}",
                )

            if cfg.get("requires_api_key", True) and not self.api_key:
                raise ConfigError(
                    user_message=f"LLM_API_KEY is required for provider '{self.provider_name}'.",
                    debug_message=f"provider={self.provider_name}, requires_api_key=True, api_key=<empty>",
                )

            class_path = cfg.get("class")
            if not class_path:
                raise ConfigError(
                    user_message=f"Provider '{self.provider_name}' is not registered and has invalid "
                    "PROVIDER_CONFIG (missing 'class').",
                    debug_message=f"provider={self.provider_name}, config={cfg}",
                )

            try:
                module_name, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                provider_cls = getattr(module, class_name)
            except (ValueError, ImportError, AttributeError) as e:
                raise ConfigError(
                    user_message=f"Failed to lazy-load provider '{self.provider_name}' from "
                    f"'{class_path}': {e}",
                    debug_message=f"provider={self.provider_name}, class_path={class_path}, error={type(e).__name__}: {e}",
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
        response = self._provider.chat(
            messages=messages,
            model=self.model,
            temperature=temperature if temperature is not None else 0.0,
            tools=tools,
            tool_choice=tool_choice,
        )
        # D8: Auto-inject token usage into the current Tracer span
        if response.usage:
            tracer = Tracer._instance
            if tracer:
                tracer.add_event("llm.end", {"token_usage": response.usage})
        return response

    def stream(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str | dict] = None,
        **kwargs,
    ) -> Iterator[LLMChunk]:
        for chunk in self._provider.chat_stream(
            messages=messages,
            model=self.model,
            temperature=temperature if temperature is not None else 0.0,
            tools=tools,
            tool_choice=tool_choice,
        ):
            if chunk.usage:
                tracer = Tracer._instance
                if tracer:
                    tracer.add_event("llm.end", {"token_usage": chunk.usage})
            yield chunk
