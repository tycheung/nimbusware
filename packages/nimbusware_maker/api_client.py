from __future__ import annotations

from typing import Any, cast

from nimbusware_client import HTTPError
from nimbusware_client.http import (
    admin_headers,
    delete,
    problem_message,
    user_headers,
)
from nimbusware_client.http import (
    get_json as _get_json,
)
from nimbusware_client.http import (
    post_json as _post_json,
)

__all__ = [
    "admin_delete",
    "admin_headers",
    "admin_post_json",
    "api_base",
    "get_json",
    "patch_json",
    "post_json",
    "user_headers",
]


def api_base() -> str:
    from nimbusware_client.http import api_base as _base

    return _base()


def get_json(path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return _get_json(path, params=params)


def patch_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    from nimbusware_client.http import request_response

    response = request_response("PATCH", path, json=payload)
    body = response.json()
    return body if isinstance(body, dict) else {}


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return _post_json(path, payload)
    except HTTPError as exc:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        if status not in {401, 403}:
            raise
        try:
            body = cast(Any, response).json()
        except ValueError:
            body = {}
        code = str(body.get("code") or "") if isinstance(body, dict) else ""
        if code in {"unauthorized", "forbidden"} or status == 403:
            msg = problem_message(body, fallback=str(exc))
            raise RuntimeError(f"Admin access required: {msg}") from exc
        raise


def admin_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _post_json(path, payload, headers={**user_headers(), **admin_headers()})


def admin_delete(path: str) -> None:
    delete(path, headers={**user_headers(), **admin_headers()})
