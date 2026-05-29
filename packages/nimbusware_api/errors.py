"""Consistent JSON error bodies for ``/v1`` ."""

from __future__ import annotations

from typing import Any


def problem(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """RFC 7807-style problem object (flat JSON, no ``type`` URI in v1)."""
    out: dict[str, Any] = {"code": code, "message": message}
    if details:
        out["details"] = details
    return out
