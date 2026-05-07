"""kagent - Pluggable AI Agent Framework"""

__version__ = "0.1.0"

from .core.config import Config, ConfigError, load_config

__all__ = ["Config", "ConfigError", "load_config"]
