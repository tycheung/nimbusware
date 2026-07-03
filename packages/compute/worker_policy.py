from __future__ import annotations

import json
from typing import Any

DEFAULT_MAX_PAYLOAD_BYTES = 512_000

_SECRET_KEY_FRAGMENTS = frozenset(
    {
        "api_key",
        "secret",
        "password",
        "token",
        "authorization",
        "connection_id",
        "secret_blob",
    },
)

_BLOCKED_ENV_PATHS = frozenset({".env", ".env.local", ".env.production"})


def _walk_strings(obj: Any, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            key_s = str(key)
            sub = f"{path}.{key_s}" if path else key_s
            if any(frag in key_s.lower() for frag in _SECRET_KEY_FRAGMENTS):
                if isinstance(val, str) and val.strip():
                    found.append((sub, val))
            found.extend(_walk_strings(val, sub))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            found.extend(_walk_strings(item, f"{path}[{idx}]"))
    return found


def payload_byte_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, default=str).encode("utf-8"))


def sanitize_work_unit_payload(
    payload: dict[str, Any] | None,
    *,
    max_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
) -> dict[str, Any]:
    """Strip secret-like keys and enforce packet size cap before host→worker send."""
    if not payload:
        return {}
    clean: dict[str, Any] = {}
    for key, val in payload.items():
        key_l = str(key).lower()
        if any(frag in key_l for frag in _SECRET_KEY_FRAGMENTS):
            continue
        if isinstance(val, str) and val.strip() in _BLOCKED_ENV_PATHS:
            continue
        clean[str(key)] = val
    if payload_byte_size(clean) > max_bytes:
        msg = f"work unit payload exceeds {max_bytes} bytes after sanitization"
        raise ValueError(msg)
    leaked = _walk_strings(clean)
    if leaked:
        msg = f"work unit payload still contains secret-like fields: {leaked[0][0]}"
        raise ValueError(msg)
    return clean
