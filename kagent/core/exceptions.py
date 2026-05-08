"""Kagent exception hierarchy"""


class KagentError(Exception):
    """Base exception for Kagent framework.

    Dual-field design:
      - user_message: safe to show end users (Chinese OK)
      - debug_message: internal details (HTTP status, stack hint, etc.)

    Backward compatible: KagentError("foo") → user_message="foo", debug_message=None
    """

    def __init__(self, user_message: str, debug_message: str | None = None):
        self.user_message = user_message
        self.debug_message = debug_message
        super().__init__(user_message)

    def __str__(self) -> str:
        return self.user_message


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
