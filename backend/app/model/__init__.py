"""Pluggable model client package."""

from app.model.base import (
    ModelClient,
    ModelClientError,
    ModelClientProtocol,
    available_providers,
    build_model_client,
    register_model_client,
)
from app.model.openai import OpenAIModelClient

__all__ = [
    "ModelClient",
    "ModelClientProtocol",
    "ModelClientError",
    "build_model_client",
    "register_model_client",
    "available_providers",
    "OpenAIModelClient",
]
