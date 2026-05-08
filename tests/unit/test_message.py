"""Tests for Message class"""

import pytest
from datetime import datetime, timezone

from kagent.core.message import Message


class TestMessage:
    """Test Message creation and serialization"""

    def test_create_message(self):
        msg = Message(content="hello", role="user")
        assert msg.content == "hello"
        assert msg.role == "user"

    def test_message_roles(self):
        for role in ("user", "assistant", "system", "tool"):
            msg = Message(content="x", role=role)
            assert msg.role == role

    def test_message_invalid_role(self):
        with pytest.raises(Exception):
            Message(content="x", role="invalid")

    def test_message_to_dict(self):
        msg = Message(content="hi", role="user")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "hi"}

    def test_message_to_dict_assistant(self):
        msg = Message(content="response", role="assistant")
        d = msg.to_dict()
        assert d == {"role": "assistant", "content": "response"}

    def test_message_timestamp_auto(self):
        msg = Message(content="test", role="user")
        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, datetime)

    def test_message_timestamp_preserved(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        msg = Message(content="test", role="user", timestamp=ts)
        assert msg.timestamp == ts

    def test_message_metadata_default(self):
        msg = Message(content="test", role="user")
        assert msg.metadata is None

    def test_message_metadata_custom(self):
        meta = {"key": "value"}
        msg = Message(content="test", role="user", metadata=meta)
        assert msg.metadata == {"key": "value"}

    def test_message_empty_content(self):
        msg = Message(content="", role="assistant")
        assert msg.content == ""
        assert msg.to_dict() == {"role": "assistant", "content": ""}
