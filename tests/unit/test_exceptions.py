"""Tests for Kagent exception hierarchy (C2: dual-field upgrade)"""

import pytest

from kagent.core.exceptions import (
    KagentError,
    LLMError,
    ConfigError,
    AgentError,
    ToolError,
)


class TestKagentErrorDualField:
    """Test dual-field user_message / debug_message"""

    def test_backward_compat_positional(self):
        """KagentError('msg') still works — user_message='msg', debug_message=None"""
        err = KagentError("something broke")
        assert err.user_message == "something broke"
        assert err.debug_message is None
        assert str(err) == "something broke"

    def test_backward_compat_keyword(self):
        """KagentError(user_message='msg') works too"""
        err = KagentError(user_message="bad input")
        assert err.user_message == "bad input"
        assert err.debug_message is None

    def test_dual_field(self):
        """Both fields accessible"""
        err = KagentError(
            user_message="LLM 调用失败",
            debug_message="HTTP 503: Service Unavailable",
        )
        assert err.user_message == "LLM 调用失败"
        assert err.debug_message == "HTTP 503: Service Unavailable"

    def test_str_returns_user_message(self):
        """__str__ returns user_message only — no debug leak"""
        err = KagentError(
            user_message="用户可见消息",
            debug_message="secret internal detail",
        )
        assert str(err) == "用户可见消息"
        assert "secret" not in str(err)

    def test_is_exception(self):
        """KagentError is still an Exception"""
        err = KagentError("test")
        assert isinstance(err, Exception)
        assert err.args == ("test",)


class TestSubclassBackwardCompat:
    """All subclasses inherit dual-field without redefining __init__"""

    @pytest.mark.parametrize("exc_cls", [LLMError, ConfigError, AgentError, ToolError])
    def test_positional_string(self, exc_cls):
        """Subclass('old style') still works"""
        err = exc_cls("old style error")
        assert err.user_message == "old style error"
        assert err.debug_message is None
        assert str(err) == "old style error"

    @pytest.mark.parametrize("exc_cls", [LLMError, ConfigError, AgentError, ToolError])
    def test_dual_field(self, exc_cls):
        """Subclass supports dual-field"""
        err = exc_cls(
            user_message="user facing",
            debug_message="internal detail",
        )
        assert err.user_message == "user facing"
        assert err.debug_message == "internal detail"

    @pytest.mark.parametrize("exc_cls", [LLMError, ConfigError, AgentError, ToolError])
    def test_isinstance_kagent_error(self, exc_cls):
        """All subclasses are instances of KagentError"""
        err = exc_cls("test")
        assert isinstance(err, KagentError)


class TestExceptionHierarchy:
    """Verify exception class hierarchy"""

    def test_llm_error_inherits(self):
        assert issubclass(LLMError, KagentError)

    def test_config_error_inherits(self):
        assert issubclass(ConfigError, KagentError)

    def test_agent_error_inherits(self):
        assert issubclass(AgentError, KagentError)

    def test_tool_error_inherits(self):
        assert issubclass(ToolError, KagentError)
