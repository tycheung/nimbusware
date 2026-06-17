"""Encrypt provider API keys at rest (v1.2 provider connection vault)."""

from __future__ import annotations

import hashlib
import os
from typing import Final

from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_env.env_flags import env_str

_VERSION: Final = b"\x01"


def _vault_key() -> bytes:
    raw = (
        env_str("NIMBUSWARE_PROVIDER_VAULT_KEY").strip()
        or nimbusware_admin_token()
        or "nimbusware-local-dev-vault"
    )
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_secret(plaintext: str) -> bytes:
    key = _vault_key()
    nonce = os.urandom(16)
    data = plaintext.encode("utf-8")
    stream = _keystream(key, nonce, len(data))
    cipher = bytes(a ^ b for a, b in zip(data, stream, strict=True))
    return _VERSION + nonce + cipher


def decrypt_secret(blob: bytes | None) -> str | None:
    if not blob:
        return None
    if blob[0:1] != _VERSION or len(blob) < 18:
        msg = "invalid provider secret blob"
        raise ValueError(msg)
    nonce = blob[1:17]
    cipher = blob[17:]
    key = _vault_key()
    stream = _keystream(key, nonce, len(cipher))
    plain = bytes(a ^ b for a, b in zip(cipher, stream, strict=True))
    return plain.decode("utf-8")
