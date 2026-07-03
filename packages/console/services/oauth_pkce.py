from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from env.oidc_config import OidcConfig


@dataclass(frozen=True)
class PkceChallenge:
    state: str
    code_verifier: str
    authorize_url: str


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def build_authorize_url(config: OidcConfig) -> PkceChallenge:
    if not config.login_ready():
        msg = "OIDC not configured"
        raise ValueError(msg)
    verifier = secrets.token_urlsafe(48)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{config.issuer}/authorize?{urlencode(params)}"
    return PkceChallenge(state=state, code_verifier=verifier, authorize_url=url)


def validate_callback_state(expected: str, received: str | None) -> bool:
    if not expected or not received:
        return False
    return secrets.compare_digest(expected, received)


def accept_oidc_callback(
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
