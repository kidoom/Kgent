"""Convenience re-exports for model clients.

Implementations live in app.model.*.
"""

from app.model.base import (
    ModelClient,
    ModelClientError,
    ModelClientProtocol,
    PromptTooLongError,
    available_providers,
    build_model_client,
    register_model_client,
)
from app.model.openai import OpenAIModelClient

__all__ = [
    "ModelClient",
    "ModelClientProtocol",
    "ModelClientError",
    "PromptTooLongError",
    "build_model_client",
    "register_model_client",
    "available_providers",
    "OpenAIModelClient",
]
