"""Kagent exception hierarchy"""


class KagentError(Exception):
    """Base exception for Kagent framework"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class LLMError(KagentError):
    """LLM provider related errors (timeout, API error, etc.)"""
    pass


class ConfigError(KagentError):
    """Configuration related errors"""
    pass


class AgentError(KagentError):
    """Agent execution errors"""
    pass


class ToolError(KagentError):
    """Tool execution errors"""
    pass
