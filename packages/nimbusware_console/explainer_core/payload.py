from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def payload_mapping(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if isinstance(payload, Mapping):
        return payload
    return None


def payload_str_field(payload: Mapping[str, Any] | None, key: str) -> str | None:
    mapping = payload_mapping(payload)
    if mapping is None:
        return None
    raw = mapping.get(key)
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped or None
