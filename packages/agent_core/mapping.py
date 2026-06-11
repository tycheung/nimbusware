from __future__ import annotations

from typing import Any


def mapping_or_empty(value: object) -> dict[str, Any]:
    """Return *value* when it is a ``dict``; otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def load_error_text(payload: object) -> str | None:
    """Non-empty ``load_error`` string from a mapping payload, if present."""
    if not isinstance(payload, dict):
        return None
    raw = payload.get("load_error")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    return text or None
