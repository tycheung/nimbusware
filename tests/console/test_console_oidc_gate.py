from __future__ import annotations

from nimbusware_env.oidc_config import load_oidc_config, oidc_required_for_console


def test_oidc_not_required_on_individual(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "individual")
    monkeypatch.setenv("NIMBUSWARE_OIDC_ENABLED", "1")
    monkeypatch.setenv("NIMBUSWARE_OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("NIMBUSWARE_OIDC_CLIENT_ID", "client")
    monkeypatch.setenv("NIMBUSWARE_OIDC_REDIRECT_URI", "http://127.0.0.1:8502/oauth/callback")
    assert not oidc_required_for_console()


def test_load_oidc_config_defaults_disabled(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_OIDC_ENABLED", raising=False)
    cfg = load_oidc_config()
    assert not cfg.enabled
