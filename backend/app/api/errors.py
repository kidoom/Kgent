"""HTTP error envelope for the runtime API."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def api_error(
    status_code: int,
    *,
    error_type: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "type": error_type,
                "message": message,
                "details": details or {},
            }
        },
    )
