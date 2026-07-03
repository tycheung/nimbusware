from __future__ import annotations

import pytest

from console.services.oauth_pkce import (
    accept_oidc_callback,
    build_authorize_url,
    validate_callback_state,
)
from env.oidc_config import OidcConfig, load_oidc_config


def test_oidc_config_issuer_valid() -> None:
    cfg = OidcConfig(
        enabled=True,
        issuer="https://idp.example.com",
        client_id="client",
        client_secret=None,
        redirect_uri="http://localhost:8502/oauth/callback",
    )
    assert cfg.login_ready()


def test_build_authorize_url_contains_pkce(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = OidcConfig(
        enabled=True,
        issuer="https://idp.example.com",
        client_id="nimbusware-admin",
        client_secret=None,
        redirect_uri="http://127.0.0.1:8502/oauth/callback",
    )
    challenge = build_authorize_url(cfg)
    assert "code_challenge=" in challenge.authorize_url
    assert challenge.state


def test_accept_oidc_callback_validates_state() -> None:
    assert validate_callback_state("abc", "abc")
    assert not validate_callback_state("abc", "xyz")
    ok, _ = accept_oidc_callback(
        code="code123",
        state="st",
        expected_state="st",
        code_verifier="verifier",
    )
    assert ok


def test_load_oidc_disabled_without_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_OIDC_ENABLED", "1")
    monkeypatch.delenv("NIMBUSWARE_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("NIMBUSWARE_OIDC_CLIENT_ID", raising=False)
    cfg = load_oidc_config()
    assert not cfg.enabled
