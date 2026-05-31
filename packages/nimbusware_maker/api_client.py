from __future__ import annotations

from typing import Any

from nimbusware_client import HTTPError
from nimbusware_client.http import (
    admin_headers,
    delete,
    get_json as _get_json,
    post_json as _post_json,
    problem_message,
    user_headers,
)

__all__ = [
    "admin_delete",
    "admin_headers",
    "admin_post_json",
    "api_base",
    "get_json",
    "post_json",
    "user_headers",
]


def api_base() -> str:
    from nimbusware_client.http import api_base as _base

    return _base()


def get_json(path: str) -> dict[str, Any]:
    return _get_json(path)


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return _post_json(path, payload)
    except HTTPError as exc:
        if exc.response.status_code in {401, 403}:
            try:
                body = exc.response.json()
            except ValueError:
                body = {}
            code = str(body.get("code") or "") if isinstance(body, dict) else ""
            if code in {"unauthorized", "forbidden"} or exc.response.status_code == 403:
                msg = problem_message(body, fallback=str(exc))
                raise RuntimeError(f"Admin access required: {msg}") from exc
        raise


def admin_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _post_json(path, payload, headers={**user_headers(), **admin_headers()})


def admin_delete(path: str) -> None:
    delete(path, headers={**user_headers(), **admin_headers()})
