from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse

from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.user import UserDep, maker_user_id_str
from nimbusware_config.provider_connections import (
    ProviderConnectionStore,
    _row_to_public,
    encode_secret_payload,
)
from nimbusware_console.services.oauth_connector import (
    accept_oauth_callback,
    build_pkce_authorize_url,
    exchange_authorization_code,
)
from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_env.env_flags import nimbusware_database_url
from nimbusware_env.subscription_oauth_config import (
    load_subscription_oauth_config,
    subscription_oauth_mock_enabled,
)
from nimbusware_iam.context import resolve_store_tenant_id
from nimbusware_orchestrator.provider_registry import (
    load_subscription_provider_presets,
    subscription_preset_by_id,
)

router = APIRouter(tags=["platform"])

_PKCE_COOKIE = "nimbusware_subscription_oauth_pkce"
_COOKIE_PATH = "/v1/platform/provider-subscriptions/oauth"
_MAKER_RETURN = "/v1/maker/app/#/models?section=desktop-subscriptions"


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


def _set_pkce_cookie(
    response: Response,
    *,
    state: str,
    code_verifier: str,
    provider_id: str,
    user_id: str,
) -> None:
    payload = {
        "state": state,
        "verifier": code_verifier,
        "provider_id": provider_id,
        "user_id": user_id,
        "exp": time.time() + 600,
    }
    response.set_cookie(
        _PKCE_COOKIE,
        _sign_payload(payload),
        httponly=True,
        samesite="lax",
        max_age=600,
        path=_COOKIE_PATH,
    )


def _read_pkce_cookie(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(_PKCE_COOKIE, "")
    return _verify_signed(raw) if raw else None


def _connection_store() -> ProviderConnectionStore:
    url = nimbusware_database_url()
    if not url:
        raise HTTPException(
            status_code=503,
            detail=problem("service_unavailable", "NIMBUSWARE_DATABASE_URL is not configured"),
        )
    return ProviderConnectionStore(url)


def _connection_user_id(request: Request) -> str:
    return maker_user_id_str(request)


def _connection_tenant_id() -> str | None:
    return str(resolve_store_tenant_id())


def _upsert_subscription_oauth(
    *,
    repo_root: Path,
    request: Request,
    provider_id: str,
    oauth_refresh_token: str | None,
) -> dict[str, Any]:
    preset = subscription_preset_by_id(repo_root, provider_id)
    if preset is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", f"unknown subscription provider: {provider_id}"),
        )
    store = _connection_store()
    user_id = _connection_user_id(request)
    secret_blob = encode_secret_payload(
        connection_kind="subscription",
        subscription_connected=True,
        oauth_refresh_token=oauth_refresh_token,
    )
    existing = [
        r
        for r in store.list_for_user(user_id=user_id, tenant_id=_connection_tenant_id())
        if r.provider_id == provider_id and r.connection_kind == "subscription"
    ]
    connection_id = existing[0].connection_id if existing else None
    row = store.upsert(
        connection_id=connection_id,
        user_id=user_id,
        tenant_id=_connection_tenant_id(),
        provider_id=provider_id,
        label=str(preset.get("label") or provider_id),
        connection_kind="subscription",
        base_url=None,
        default_model_id=None,
        secret_blob=secret_blob,
    )
    return _row_to_public(row)


def _config_for_provider(repo_root: Path, provider_id: str):
    cfg = load_subscription_oauth_config(provider_id)
    preset = subscription_preset_by_id(repo_root, provider_id) or {}
    oauth_block = preset.get("oauth")
    if isinstance(oauth_block, dict):
        scopes = oauth_block.get("scopes")
        if isinstance(scopes, str) and scopes.strip():
            cfg = replace(cfg, scopes=scopes.strip())
    return cfg


@router.get("/platform/provider-subscriptions/oauth/status")
def subscription_oauth_status(orch: OrchDep, _: UserDep) -> dict[str, Any]:
    providers: list[dict[str, Any]] = []
    for preset in load_subscription_provider_presets(orch.repo_root):
        provider_id = str(preset.get("id") or "")
        cfg = _config_for_provider(orch.repo_root, provider_id)
        providers.append(
            {
                "provider_id": provider_id,
                "label": preset.get("label"),
                "oauth_ready": cfg.login_ready(),
                "scopes": cfg.scopes,
                "authorize_path": (
                    f"/v1/platform/provider-subscriptions/{provider_id}/oauth/authorize"
                ),
                "configure_hint": (
                    "Set NIMBUSWARE_SUBSCRIPTION_OAUTH_ISSUER and "
                    "NIMBUSWARE_SUBSCRIPTION_OAUTH_CLIENT_ID "
                    f"(optional per-provider: NIMBUSWARE_SUBSCRIPTION_OAUTH_{provider_id.upper()}_ISSUER)"
                ),
            },
        )
    return {
        "providers": providers,
        "callback_path": "/v1/platform/provider-subscriptions/oauth/callback",
        "mock_mode": subscription_oauth_mock_enabled(),
    }


@router.get("/platform/provider-subscriptions/{provider_id}/oauth/authorize")
def subscription_oauth_authorize(
    provider_id: str,
    request: Request,
    orch: OrchDep,
    _: UserDep,
) -> RedirectResponse:
    preset = subscription_preset_by_id(orch.repo_root, provider_id)
    if preset is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", f"unknown subscription provider: {provider_id}"),
        )
    cfg = _config_for_provider(orch.repo_root, provider_id)
    if not cfg.login_ready():
        raise HTTPException(
            status_code=503,
            detail=problem(
                "oauth_not_configured",
                "Subscription OAuth is not configured for this install",
            ),
        )
    challenge = build_pkce_authorize_url(cfg)
    user_id = _connection_user_id(request)
    if subscription_oauth_mock_enabled():
        url = (
            "/v1/platform/provider-subscriptions/oauth/mock-authorize"
            f"?provider_id={quote(provider_id)}"
            f"&state={quote(challenge.state)}"
            f"&code_verifier={quote(challenge.code_verifier)}"
        )
        response = RedirectResponse(url=url, status_code=302)
    else:
        response = RedirectResponse(url=challenge.authorize_url, status_code=302)
    _set_pkce_cookie(
        response,
        state=challenge.state,
        code_verifier=challenge.code_verifier,
        provider_id=provider_id,
        user_id=user_id,
    )
    return response


@router.get("/platform/provider-subscriptions/oauth/mock-authorize")
def subscription_oauth_mock_authorize(
    request: Request,
    _: UserDep,
    provider_id: str = Query(...),
    state: str = Query(...),
    code_verifier: str = Query(...),
) -> RedirectResponse:
    if not subscription_oauth_mock_enabled():
        raise HTTPException(status_code=404, detail=problem("not_found", "mock authorize disabled"))
    url = (
        "/v1/platform/provider-subscriptions/oauth/callback"
        f"?code=mock_subscription_oauth_code&state={quote(state)}"
    )
    response = RedirectResponse(url=url, status_code=302)
    _set_pkce_cookie(
        response,
        state=state,
        code_verifier=code_verifier,
        provider_id=provider_id,
        user_id=_connection_user_id(request),
    )
    return response


@router.get("/platform/provider-subscriptions/oauth/callback")
def subscription_oauth_callback(
    request: Request,
    orch: OrchDep,
    _: UserDep,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    if error:
        detail = error_description or error
        raise HTTPException(
            status_code=401,
            detail=problem("oauth_callback_failed", f"IdP returned error: {detail}"),
        )
    pkce = _read_pkce_cookie(request)
    if not pkce:
        raise HTTPException(
            status_code=400,
            detail=problem("oauth_pkce_missing", "OAuth PKCE session expired; restart connect"),
        )
    provider_id = str(pkce.get("provider_id") or "")
    ok, msg = accept_oauth_callback(
        code=code,
        state=state,
        expected_state=str(pkce.get("state", "")),
        code_verifier=str(pkce.get("verifier", "")),
    )
    if not ok:
        raise HTTPException(status_code=401, detail=problem("oauth_callback_failed", msg))
    cfg = _config_for_provider(orch.repo_root, provider_id)
    refresh_token: str | None = None
    if subscription_oauth_mock_enabled():
        refresh_token = "mock_refresh_token"
    else:
        try:
            tokens = exchange_authorization_code(
                cfg,
                code=str(code),
                code_verifier=str(pkce.get("verifier", "")),
            )
            raw_refresh = tokens.get("refresh_token")
            if isinstance(raw_refresh, str) and raw_refresh.strip():
                refresh_token = raw_refresh.strip()
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=problem("oauth_token_exchange_failed", str(exc)),
            ) from exc
    _upsert_subscription_oauth(
        repo_root=orch.repo_root,
        request=request,
        provider_id=provider_id,
        oauth_refresh_token=refresh_token,
    )
    return_url = (
        f"{_MAKER_RETURN}&oauth=linked&provider_id={quote(provider_id)}"
    )
    response = RedirectResponse(url=return_url, status_code=302)
    response.delete_cookie(_PKCE_COOKIE, path=_COOKIE_PATH)
    return response
