from __future__ import annotations

import os
from typing import Any

import httpx

from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_iam.constants import API_KEY_HEADER


def api_base() -> str:
    return os.environ.get("NIMBUSWARE_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/")


def user_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.environ.get("NIMBUSWARE_API_KEY", "").strip()
    if api_key:
        headers[API_KEY_HEADER] = api_key
    return headers


def admin_headers() -> dict[str, str]:
    return {"X-Nimbusware-Admin-Token": nimbusware_admin_token()}


def _raise_with_admin_hint(exc: httpx.HTTPStatusError) -> None:
    if exc.response.status_code in {401, 403}:
        try:
            body = exc.response.json()
        except ValueError:
            body = {}
        code = str(body.get("code") or "")
        if code in {"unauthorized", "forbidden"} or exc.response.status_code == 403:
            msg = str(body.get("message") or body.get("detail") or exc)
            raise RuntimeError(f"Admin access required: {msg}") from exc
    raise exc


def get_json(path: str) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        r = client.get(f"{api_base()}{path}", headers=user_headers())
        r.raise_for_status()
        body = r.json()
        return body if isinstance(body, dict) else {"data": body}


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{api_base()}{path}", json=payload, headers=user_headers())
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _raise_with_admin_hint(exc)
        body = r.json()
        return body if isinstance(body, dict) else {"data": body}


def admin_post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        headers = {**user_headers(), **admin_headers()}
        r = client.post(f"{api_base()}{path}", json=payload, headers=headers)
        r.raise_for_status()
        body = r.json()
        return body if isinstance(body, dict) else {"data": body}


def admin_delete(path: str) -> None:
    with httpx.Client(timeout=15.0) as client:
        headers = {**user_headers(), **admin_headers()}
        r = client.delete(f"{api_base()}{path}", headers=headers)
        r.raise_for_status()
