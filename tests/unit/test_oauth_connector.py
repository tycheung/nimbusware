from __future__ import annotations

from unittest.mock import MagicMock, patch

from nimbusware_console.services.oauth_connector import (
    accept_oauth_callback,
    build_pkce_authorize_url,
    exchange_authorization_code,
    validate_callback_state,
)
from nimbusware_env.subscription_oauth_config import SubscriptionOAuthConfig


def _cfg() -> SubscriptionOAuthConfig:
    return SubscriptionOAuthConfig(
        issuer="https://tenant.auth0.com",
        client_id="desktop-client",
        client_secret=None,
        redirect_uri="http://127.0.0.1:8000/v1/platform/provider-subscriptions/oauth/callback",
        scopes="openid profile offline_access",
    )


def test_build_pkce_authorize_url_uses_issuer_authorize_fallback() -> None:
    challenge = build_pkce_authorize_url(_cfg())
    assert challenge.state
    assert challenge.code_verifier
    assert "client_id=desktop-client" in challenge.authorize_url
    assert "code_challenge=" in challenge.authorize_url
    assert challenge.authorize_url.startswith("https://tenant.auth0.com/authorize?")


def test_accept_oauth_callback_validates_state() -> None:
    ok, msg = accept_oauth_callback(
        code="abc",
        state="state-1",
        expected_state="state-1",
        code_verifier="verifier",
    )
    assert ok is True
    assert msg == "ok"
    assert validate_callback_state("state-1", "state-1") is True
    assert validate_callback_state("state-1", "other") is False


def test_exchange_authorization_code_posts_to_token_endpoint() -> None:
    cfg = _cfg()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "access_token": "at",
        "refresh_token": "rt",
        "token_type": "Bearer",
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = mock_resp
    with patch(
        "nimbusware_console.services.oauth_connector.issuer_endpoints",
        return_value={
            "authorization_endpoint": "https://tenant.auth0.com/authorize",
            "token_endpoint": "https://tenant.auth0.com/oauth/token",
        },
    ):
        with patch(
            "nimbusware_console.services.oauth_connector.httpx.Client", return_value=mock_client
        ):
            tokens = exchange_authorization_code(cfg, code="code-1", code_verifier="verifier-1")
    assert tokens["refresh_token"] == "rt"
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[0][0] == "https://tenant.auth0.com/oauth/token"
    assert call_kwargs[1]["data"]["code"] == "code-1"
    assert call_kwargs[1]["data"]["code_verifier"] == "verifier-1"
