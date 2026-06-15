from __future__ import annotations

import os
from typing import Any

import httpx
from httpx import HTTPError, Response

from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_iam.constants import API_KEY_HEADER

ADMIN_TOKEN_HEADER = "X-Nimbusware-Admin-Token"


def api_base() -> str:
    from nimbusware_env.env_flags import nimbusware_api_base_url

    return nimbusware_api_base_url()


def user_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.environ.get("NIMBUSWARE_API_KEY", "").strip()
    if api_key:
        headers[API_KEY_HEADER] = api_key
    return headers


def admin_headers() -> dict[str, str]:
    return {ADMIN_TOKEN_HEADER: nimbusware_admin_token()}


def admin_token_headers(token: str) -> dict[str, str]:
    trimmed = token.strip()
    return {ADMIN_TOKEN_HEADER: trimmed} if trimmed else {}


def problem_message(body: object, *, fallback: str = "") -> str:
    if isinstance(body, dict):
        msg = body.get("message") or body.get("detail")
        if msg:
            return str(msg)
    return fallback


def request_response(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    with httpx.Client(timeout=timeout) as client:
        response = client.request(
            method,
            f"{api_base()}{path}",
            params=params,
            json=json,
            headers=headers if headers is not None else user_headers(),
        )
        if raise_for_status:
            response.raise_for_status()
        return response


def get_json(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = get_response(
        path,
        params=params,
        timeout=timeout,
        headers=headers,
    )
    body = response.json()
    return body if isinstance(body, dict) else {"data": body}


def get_response(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    return request_response(
        "GET",
        path,
        params=params,
        timeout=timeout,
        headers=headers,
        raise_for_status=raise_for_status,
    )


def post_response(
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    return request_response(
        "POST",
        path,
        json=payload if payload is not None else {},
        timeout=timeout,
        headers=headers,
        raise_for_status=raise_for_status,
    )


def post_json(
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = post_response(
        path,
        payload=payload,
        timeout=timeout,
        headers=headers,
    )
    body = response.json()
    return body if isinstance(body, dict) else {"data": body}


def patch_response(
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    return request_response(
        "PATCH",
        path,
        json=payload,
        timeout=timeout,
        headers=headers,
        raise_for_status=raise_for_status,
    )


def put_response(
    path: str,
    payload: dict[str, Any],
    *,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    return request_response(
        "PUT",
        path,
        json=payload,
        timeout=timeout,
        headers=headers,
        raise_for_status=raise_for_status,
    )


def delete_response(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    return request_response(
        "DELETE",
        path,
        params=params,
        timeout=timeout,
        headers=headers,
        raise_for_status=raise_for_status,
    )


def delete(path: str, *, timeout: float = 15.0, headers: dict[str, str] | None = None) -> None:
    delete_response(path, timeout=timeout, headers=headers)


def stream_collect_text(
    path: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    max_bytes: int = 256_000,
) -> str:
    hdrs = headers if headers is not None else user_headers()
    chunks: list[str] = []
    size = 0
    with httpx.Client(timeout=timeout) as client:
        with client.stream(
            "GET",
            f"{api_base()}{path}",
            params=params,
            headers=hdrs,
        ) as response:
            response.raise_for_status()
            for part in response.iter_text():
                chunks.append(part)
                size += len(part.encode("utf-8", errors="ignore"))
                if size >= max_bytes:
                    break
    return "".join(chunks)


__all__ = [
    "ADMIN_TOKEN_HEADER",
    "HTTPError",
    "Response",
    "admin_headers",
    "admin_token_headers",
    "api_base",
    "delete",
    "delete_response",
    "get_json",
    "get_response",
    "patch_response",
    "post_json",
    "post_response",
    "problem_message",
    "stream_collect_text",
    "user_headers",
]
