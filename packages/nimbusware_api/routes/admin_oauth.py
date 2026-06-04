"""Admin Console OIDC login (Enterprise) — authorization code + PKCE."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from nimbusware_api.errors import problem
from nimbusware_console.services.oauth_pkce import accept_oidc_callback, build_authorize_url
from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_env.edition import is_enterprise
from nimbusware_env.env_flags import env_truthy
from nimbusware_env.oidc_config import load_oidc_config

router = APIRouter(prefix="/admin/oauth", tags=["admin"])

_PKCE_COOKIE = "nimbusware_oidc_pkce"
_SESSION_COOKIE = "nimbusware_oidc_session"
_COOKIE_MAX_AGE = 3600


def _require_enterprise_oauth() -> None:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_edition_required",
                "OIDC login requires NIMBUSWARE_EDITION=enterprise",
            ),
        )


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


def _set_pkce_cookie(response: Response, *, state: str, code_verifier: str) -> None:
    payload = {"state": state, "verifier": code_verifier, "exp": time.time() + 600}
    response.set_cookie(
        _PKCE_COOKIE,
        _sign_payload(payload),
        httponly=True,
        samesite="lax",
        max_age=600,
        path="/v1/admin/oauth",
    )


def _read_pkce_cookie(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(_PKCE_COOKIE, "")
    return _verify_signed(raw) if raw else None


def _set_session_cookie(response: Response) -> None:
    payload = {"ok": True, "exp": time.time() + _COOKIE_MAX_AGE}
    response.set_cookie(
        _SESSION_COOKIE,
        _sign_payload(payload),
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _session_valid(request: Request) -> bool:
    raw = request.cookies.get(_SESSION_COOKIE, "")
    data = _verify_signed(raw) if raw else None
    return bool(data and data.get("ok"))


@router.get("/login")
def admin_oauth_login() -> RedirectResponse:
    _require_enterprise_oauth()
    cfg = load_oidc_config()
    if not cfg.login_ready():
        raise HTTPException(
            status_code=503,
            detail=problem("oidc_not_configured", "OIDC is not configured for this install"),
        )
    challenge = build_authorize_url(cfg)
    if env_truthy("NIMBUSWARE_OIDC_MOCK"):
        url = (
            "/v1/admin/oauth/mock-authorize"
            f"?state={challenge.state}&code_verifier={challenge.code_verifier}"
        )
        response = RedirectResponse(url=url, status_code=302)
    else:
        response = RedirectResponse(url=challenge.authorize_url, status_code=302)
    _set_pkce_cookie(response, state=challenge.state, code_verifier=challenge.code_verifier)
    return response


@router.get("/mock-authorize")
def admin_oauth_mock_authorize(
    state: str = Query(...),
    code_verifier: str = Query(...),
) -> RedirectResponse:
    _require_enterprise_oauth()
    if not env_truthy("NIMBUSWARE_OIDC_MOCK"):
        raise HTTPException(status_code=404, detail=problem("not_found", "mock authorize disabled"))
    url = f"/v1/admin/oauth/callback?code=mock_oidc_code&state={state}"
    response = RedirectResponse(url=url, status_code=302)
    _set_pkce_cookie(response, state=state, code_verifier=code_verifier)
    return response


@router.get("/callback")
def admin_oauth_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> RedirectResponse:
    _require_enterprise_oauth()
    pkce = _read_pkce_cookie(request)
    if not pkce:
        raise HTTPException(
            status_code=400,
            detail=problem("oidc_pkce_missing", "OIDC PKCE session expired; restart login"),
        )
    ok, msg = accept_oidc_callback(
        code=code,
        state=state,
        expected_state=str(pkce.get("state", "")),
        code_verifier=str(pkce.get("verifier", "")),
    )
    if not ok:
        raise HTTPException(status_code=401, detail=problem("oidc_callback_failed", msg))
    response = RedirectResponse(url="/v1/admin/app/", status_code=302)
    _set_session_cookie(response)
    response.delete_cookie(_PKCE_COOKIE, path="/v1/admin/oauth")
    return response


@router.get("/session")
def admin_oauth_session(request: Request) -> dict[str, bool]:
    _require_enterprise_oauth()
    return {"authenticated": _session_valid(request)}


@router.post("/logout")
def admin_oauth_logout() -> Response:
    _require_enterprise_oauth()
    response = JSONResponse({"ok": True})
    response.delete_cookie(_SESSION_COOKIE, path="/")
    return response
