"""API key generation and verification (Lane D / fo201)."""

from __future__ import annotations

import hashlib
import secrets


def generate_api_key(*, prefix: str = "nwb") -> str:
    token = secrets.token_urlsafe(32)
    return f"{prefix}_{token}"


def api_key_prefix(api_key: str) -> str:
    return api_key[:12]


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
