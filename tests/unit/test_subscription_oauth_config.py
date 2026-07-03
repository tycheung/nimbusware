from __future__ import annotations

from env.subscription_oauth_config import (
    load_subscription_oauth_config,
    subscription_oauth_mock_enabled,
)


def test_subscription_oauth_config_global_env(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_ISSUER", "https://tenant.auth0.com")
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_CLIENT_ID", "desktop-client")
    monkeypatch.setenv(
        "NIMBUSWARE_SUBSCRIPTION_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/v1/platform/provider-subscriptions/oauth/callback",
    )
    cfg = load_subscription_oauth_config("chatgpt_plus")
    assert cfg.login_ready() is True
    assert cfg.issuer == "https://tenant.auth0.com"
    assert cfg.client_id == "desktop-client"
    assert "offline_access" in cfg.scopes


def test_subscription_oauth_config_per_provider_override(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_ISSUER", "https://global.example.com")
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_CLIENT_ID", "global-client")
    monkeypatch.setenv(
        "NIMBUSWARE_SUBSCRIPTION_OAUTH_CLAUDE_PRO_ISSUER",
        "https://claude-tenant.auth0.com",
    )
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_CLAUDE_PRO_CLIENT_ID", "claude-client")
    monkeypatch.setenv(
        "NIMBUSWARE_SUBSCRIPTION_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/v1/platform/provider-subscriptions/oauth/callback",
    )
    chatgpt = load_subscription_oauth_config("chatgpt_plus")
    claude = load_subscription_oauth_config("claude_pro")
    assert chatgpt.issuer == "https://global.example.com"
    assert claude.issuer == "https://claude-tenant.auth0.com"
    assert claude.client_id == "claude-client"


def test_subscription_oauth_mock_flag(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_MOCK", raising=False)
    assert subscription_oauth_mock_enabled() is False
    monkeypatch.setenv("NIMBUSWARE_SUBSCRIPTION_OAUTH_MOCK", "1")
    assert subscription_oauth_mock_enabled() is True
