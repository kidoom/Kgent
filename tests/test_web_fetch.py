"""Tests for WebFetchTool."""

from __future__ import annotations

import pytest

from app.tools.web_fetch import WebFetchTool, _strip_html


@pytest.mark.asyncio
async def test_reject_non_http() -> None:
    tool = WebFetchTool()
    with pytest.raises(ValueError, match="http/https"):
        await tool.call({"url": "file:///etc/passwd"})


@pytest.mark.asyncio
async def test_reject_ftp() -> None:
    tool = WebFetchTool()
    with pytest.raises(ValueError, match="http/https"):
        await tool.call({"url": "ftp://example.com"})


def test_strip_html_basic() -> None:
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_scripts() -> None:
    html = '<div>text<script>alert("xss")</script> more</div>'
    assert "text" in _strip_html(html)
    assert "alert" not in _strip_html(html)


def test_strip_html_entities() -> None:
    assert _strip_html("a &amp; b &lt; c") == "a b c"
