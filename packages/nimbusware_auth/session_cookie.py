from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from uuid import UUID

from fastapi import Request, Response

from nimbusware_env.admin_token import nimbusware_admin_token

AUTH_SESSION_COOKIE = "nimbusware_auth_session"
_COOKIE_MAX_AGE = 7 * 24 * 3600


def _sign_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(
        nimbusware_admin_token().encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    raw = base64.urlsafe_b64encode(body).decode("ascii")
    return f"{raw}.{sig}"


def _verify_signed(blob: str) -> dict[str, Any] | None:
    if "." not in blob:
        return None
    raw, sig = blob.rsplit(".", 1)
    try:
        body = base64.urlsafe_b64decode(raw.encode("ascii"))
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    expected = hmac.new(
        nimbusware_admin_token().encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    exp = payload.get("exp")
    if isinstance(exp, (int, float)) and time.time() > float(exp):
        return None
    return payload


def set_auth_session_cookie(response: Response, *, user_id: UUID) -> None:
    payload = {
        "user_id": str(user_id),
        "exp": time.time() + _COOKIE_MAX_AGE,
    }
    response.set_cookie(
        AUTH_SESSION_COOKIE,
        _sign_payload(payload),
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def clear_auth_session_cookie(response: Response) -> None:
    response.delete_cookie(AUTH_SESSION_COOKIE, path="/")


def user_id_from_request(request: Request) -> UUID | None:
    blob = request.cookies.get(AUTH_SESSION_COOKIE)
    if not blob:
        return None
    payload = _verify_signed(blob)
    if payload is None:
        return None
    raw = payload.get("user_id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return UUID(raw.strip())
    except ValueError:
        return None
