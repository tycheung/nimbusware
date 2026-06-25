from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from nimbusware_env.subscription_oauth_config import SubscriptionOAuthConfig


@dataclass(frozen=True)
class PkceChallenge:
    state: str
    code_verifier: str
    authorize_url: str


_discovery_cache: dict[str, dict[str, str]] = {}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def discover_oidc_endpoints(issuer: str) -> dict[str, str]:
    base = issuer.rstrip("/")
    cached = _discovery_cache.get(base)
    if cached is not None:
        return cached
    url = f"{base}/.well-known/openid-configuration"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        doc = resp.json()
    endpoints = {
        "authorization_endpoint": str(doc["authorization_endpoint"]),
        "token_endpoint": str(doc["token_endpoint"]),
    }
    _discovery_cache[base] = endpoints
    return endpoints


def issuer_endpoints(issuer: str) -> dict[str, str]:
    base = issuer.rstrip("/")
    try:
        return discover_oidc_endpoints(base)
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return {
            "authorization_endpoint": f"{base}/authorize",
            "token_endpoint": f"{base}/oauth/token",
        }


def build_pkce_authorize_url(
    config: SubscriptionOAuthConfig,
    *,
    extra_params: dict[str, str] | None = None,
) -> PkceChallenge:
    if not config.login_ready():
        msg = "subscription OAuth not configured"
        raise ValueError(msg)
    verifier = secrets.token_urlsafe(48)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    state = secrets.token_urlsafe(24)
    params: dict[str, str] = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scopes,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if extra_params:
        params.update(extra_params)
    endpoints = issuer_endpoints(config.issuer)
    url = f"{endpoints['authorization_endpoint']}?{urlencode(params)}"
    return PkceChallenge(state=state, code_verifier=verifier, authorize_url=url)


def validate_callback_state(expected: str, received: str | None) -> bool:
    if not expected or not received:
        return False
    return secrets.compare_digest(expected, received)


def exchange_authorization_code(
    config: SubscriptionOAuthConfig,
    *,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    endpoints = issuer_endpoints(config.issuer)
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config.redirect_uri,
        "client_id": config.client_id,
        "code_verifier": code_verifier,
    }
    if config.client_secret:
        data["client_secret"] = config.client_secret
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            endpoints["token_endpoint"],
            data=data,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        body = resp.json()
    if not isinstance(body, dict):
        msg = "token endpoint returned non-object JSON"
        raise ValueError(msg)
    return body


def accept_oauth_callback(
    *,
    code: str | None,
    state: str | None,
    expected_state: str,
    code_verifier: str,
) -> tuple[bool, str]:
    if not code or not code.strip():
        return False, "missing authorization code"
    if not validate_callback_state(expected_state, state):
        return False, "invalid OAuth state"
    if not code_verifier:
        return False, "missing PKCE verifier"
    return True, "ok"
