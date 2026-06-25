from __future__ import annotations

from pathlib import Path

from nimbusware_api.routes.provider_subscription_oauth import _config_for_provider

REPO = Path(__file__).resolve().parents[2]


def test_config_for_provider_uses_yaml_oauth_scopes(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_ISSUER", "https://tenant.auth0.com")
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_CLIENT_ID", "desktop-client")
    monkeypatch.setenv(
        "NIMBUSWARE_SUBSCRIPTION_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/v1/platform/provider-subscriptions/oauth/callback",
    )
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_SCOPES", "openid")
    cfg = _config_for_provider(REPO, "chatgpt_plus")
    assert cfg.scopes == "openid profile offline_access"
