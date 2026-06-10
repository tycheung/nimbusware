"""Small helpers for untyped event/metadata dicts."""

from __future__ import annotations

from typing import Any


def mapping_or_empty(value: object) -> dict[str, Any]:
    """Return *value* when it is a ``dict``; otherwise an empty dict."""
    return value if isinstance(value, dict) else {}
