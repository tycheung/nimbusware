from __future__ import annotations

from typing import Any


def mapping_or_empty(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def field_error_text(payload: object, field: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get(field)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    return text or None


def load_error_text(payload: object) -> str | None:
    return field_error_text(payload, "load_error")
