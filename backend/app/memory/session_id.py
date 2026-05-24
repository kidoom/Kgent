"""Shared session_id validation for API and persistence."""

from __future__ import annotations

import re

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def validate_session_id(session_id: str) -> None:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError(
            "session_id must be 1-80 chars of letters, digits, underscore, or hyphen"
        )
