"""Fetch URL content as plain text."""

from __future__ import annotations

import re
import urllib.request
import urllib.error
from typing import Any

_MAX_BODY_BYTES = 50_000
_TIMEOUT_SECONDS = 15


class WebFetchTool:
    name = "web_fetch"
    description = (
        "Fetch a URL and return its content as plain text. "
        "HTML tags are stripped. Only http/https URLs are accepted."
    )
    risk_level = "medium"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch (must start with http:// or https://).",
            },
        },
        "required": ["url"],
        "additionalProperties": False,
    }

    async def call(self, input: dict[str, Any]) -> str:
        url = input.get("url")
        if not url:
            raise ValueError("web_fetch requires a 'url' string")

        if not url.startswith(("http://", "https://")):
            raise ValueError(f"only http/https URLs are supported, got: {url}")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Kgent/0.1"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
                raw = resp.read(_MAX_BODY_BYTES + 1)
        except urllib.error.HTTPError as exc:
            return f"[HTTP {exc.code}: {exc.reason}]"
        except urllib.error.URLError as exc:
            return f"[fetch error: {exc.reason}]"
        except Exception as exc:
            return f"[fetch error: {exc}]"

        truncated = len(raw) > _MAX_BODY_BYTES
        text = raw[:_MAX_BODY_BYTES].decode(errors="replace")
        text = _strip_html(text)
        if truncated:
            text += "\n...[truncated at 50KB]"
        return text


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
