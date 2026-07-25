from __future__ import annotations

import os

_DEFAULT_BASE_URL = "http://127.0.0.1:8787"
_BROKER_HTTP_ENV = "NIMBUSWARE_BROKER_HTTP"
_BROKER_TOKEN_ENV = "NIMBUSWARE_BROKER_TOKEN"


def normalize_base_url(raw: str) -> str:
    return raw.strip().rstrip("/")


def resolve_base_url(base_url: str | None) -> str:
    raw = base_url if base_url is not None else os.environ.get(_BROKER_HTTP_ENV, _DEFAULT_BASE_URL)
    return normalize_base_url(raw)


def resolve_token(token: str | None) -> str:
    if token is not None:
        return token.strip()
    return os.environ.get(_BROKER_TOKEN_ENV, "").strip()


def auth_headers(token: str) -> dict[str, str]:
    trimmed = token.strip()
    if not trimmed:
        return {}
    return {"Authorization": f"Bearer {trimmed}"}


def __getattr__(name: str):
    if name == "get_json":
        from broker_client.http_get import get_json

        return get_json
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
