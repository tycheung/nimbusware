"""Consistent JSON error bodies for ``/v1``."""

from __future__ import annotations

from typing import Any


def problem(
    code: str,
    message: str,
    *,
    type: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """RFC 7807-style problem object (flat JSON; optional ``type`` URI).

    When ``type`` is omitted (default), the body keeps the v1 flat shape
    (``code``, ``message``, optional ``details`` only).
    """
    out: dict[str, Any] = {"code": code, "message": message}
    if type is not None:
        out["type"] = type
    if details:
        out["details"] = details
    return out
