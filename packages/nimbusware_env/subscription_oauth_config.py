from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from nimbusware_env.env_flags import env_str, env_truthy


@dataclass(frozen=True)
class SubscriptionOAuthConfig:
    issuer: str
    client_id: str
    client_secret: str | None
    redirect_uri: str
    scopes: str

    def issuer_valid(self) -> bool:
        if not self.issuer:
            return False
        parsed = urlparse(self.issuer)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def login_ready(self) -> bool:
        return self.issuer_valid() and bool(self.client_id) and bool(self.redirect_uri)


def _provider_env_suffix(provider_id: str) -> str:
    return provider_id.strip().upper().replace("-", "_")


def _resolve_env(name: str, *, provider_id: str | None = None) -> str:
    if provider_id:
        specific = env_str(
            f"NIMBUSWARE_SUBSCRIPTION_OAUTH_{_provider_env_suffix(provider_id)}_{name}",
        ).strip()
        if specific:
            return specific
    return env_str(f"NIMBUSWARE_SUBSCRIPTION_OAUTH_{name}").strip()


def _default_redirect_uri() -> str:
    redirect = _resolve_env("REDIRECT_URI")
    if redirect:
        return redirect
    base = env_str("NIMBUSWARE_API_BASE").strip().rstrip("/")
    if base:
        return f"{base}/platform/provider-subscriptions/oauth/callback"
    port = env_str("PORT").strip() or env_str("NIMBUSWARE_API_PORT").strip() or "8000"
    return f"http://127.0.0.1:{port}/v1/platform/provider-subscriptions/oauth/callback"


def load_subscription_oauth_config(provider_id: str) -> SubscriptionOAuthConfig:
    issuer = _resolve_env("ISSUER", provider_id=provider_id).rstrip("/")
    client_id = _resolve_env("CLIENT_ID", provider_id=provider_id)
    secret = _resolve_env("CLIENT_SECRET", provider_id=provider_id) or None
    redirect = _resolve_env("REDIRECT_URI", provider_id=provider_id) or _default_redirect_uri()
    scopes = _resolve_env("SCOPES", provider_id=provider_id) or "openid profile offline_access"
    return SubscriptionOAuthConfig(
        issuer=issuer,
        client_id=client_id,
        client_secret=secret,
        redirect_uri=redirect,
        scopes=scopes,
    )


def subscription_oauth_mock_enabled() -> bool:
    return env_truthy("NIMBUSWARE_SUBSCRIPTION_OAUTH_MOCK")
