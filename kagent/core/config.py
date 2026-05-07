"""Config module: Configuration management for Kagent"""

import os
from typing import Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .exceptions import ConfigError


class Config(BaseModel):
    """Configuration model for Kagent framework"""

    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    debug: bool = False
    log_level: str = "INFO"
    max_history_length: int = 50
    max_steps: int = 5
    trace_enabled: bool = True
    trace_export: str = "console"

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables.

        Args:
            env_file: Path to .env file. If None, searches for .env in current directory.

        Returns:
            Config instance with values from environment.

        Raises:
            ConfigError: If required configuration is missing or invalid.
        """
        # Load .env file if it exists
        load_dotenv(env_file)

        # Map environment variables to config fields
        config_data = {
            "default_provider": os.getenv("LLM_PROVIDER", "openai"),
            "default_model": os.getenv("LLM_MODEL_ID", "gpt-4o"),
            "api_key": os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv("LLM_BASE_URL"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS")) if os.getenv("LLM_MAX_TOKENS") else None,
            "debug": os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "max_history_length": int(os.getenv("MAX_HISTORY_LENGTH", "50")),
            "max_steps": int(os.getenv("MAX_STEPS", "5")),
            "trace_enabled": os.getenv("TRACE_ENABLED", "true").lower() in ("true", "1", "yes"),
            "trace_export": os.getenv("TRACE_EXPORT", "console"),
        }

        config = cls(**config_data)
        config.validate_config()
        return config

    def validate_config(self) -> None:
        """Validate configuration.

        Raises:
            ConfigError: If required configuration is missing or invalid.
        """
        # Skip API key validation for providers that don't need it
        providers_without_api_key = {"ollama", "vllm"}

        if self.default_provider not in providers_without_api_key:
            if not self.api_key:
                raise ConfigError(
                    f"LLM_API_KEY is required for provider '{self.default_provider}'. "
                    f"Set it in .env file or environment variable."
                )


# Convenience function
def load_config(env_file: Optional[str] = None) -> Config:
    """Load configuration from environment."""
    return Config.from_env(env_file)
