"""Model client protocol, registry, and shared types."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.agent.messages import Message, ModelResponse


# ---------------------------------------------------------------------------
# Error type — all providers wrap external failures into this.
# ---------------------------------------------------------------------------

class ModelClientError(Exception):
    """Raised when a model provider fails (network, auth, parse, etc.)."""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ModelClientProtocol(Protocol):
    async def call_model(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelResponse:
        """Return normalized assistant output."""
        ...


# Backward-compatible alias
ModelClient = ModelClientProtocol


# ---------------------------------------------------------------------------
# Pluggable provider registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[ModelClientProtocol]] = {}


def register_model_client(name: str):
    """Class decorator — registers a ModelClient implementation under *name*."""
    def decorator(cls: type[ModelClientProtocol]) -> type[ModelClientProtocol]:
        _REGISTRY[name] = cls
        return cls
    return decorator


def available_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_REGISTRY)


def build_model_client(kind: str, **kwargs: Any) -> ModelClientProtocol:
    """Create a ModelClient by registry name.

    Raises ModelClientError when *kind* is unknown or instantiation fails.
    """
    cls = _REGISTRY.get(kind)
    if cls is None:
        raise ModelClientError(
            f"Unknown model client '{kind}'. "
            f"Available: {', '.join(available_providers()) or '(none)'}"
        )
    try:
        return cls(**kwargs)  # type: ignore[call-arg]
    except TypeError as exc:
        raise ModelClientError(f"Cannot instantiate model client '{kind}': {exc}") from exc
