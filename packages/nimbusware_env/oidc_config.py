from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from nimbusware_env.env_flags import env_str, env_truthy


@dataclass(frozen=True)
class OidcConfig:
    enabled: bool
    issuer: str
    client_id: str
    client_secret: str | None
    redirect_uri: str

    def issuer_valid(self) -> bool:
        if not self.issuer:
            return False
        parsed = urlparse(self.issuer)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def login_ready(self) -> bool:
        return (
            self.enabled
            and self.issuer_valid()
            and bool(self.client_id)
            and bool(self.redirect_uri)
        )


def load_oidc_config() -> OidcConfig:
    issuer = env_str("NIMBUSWARE_OIDC_ISSUER").strip().rstrip("/")
    client_id = env_str("NIMBUSWARE_OIDC_CLIENT_ID").strip()
    secret = env_str("NIMBUSWARE_OIDC_CLIENT_SECRET").strip() or None
    redirect = env_str("NIMBUSWARE_OIDC_REDIRECT_URI").strip()
    if not redirect:
        redirect = env_str("NIMBUSWARE_ADMIN_CONSOLE_URL").strip()
        if redirect:
            redirect = f"{redirect.rstrip('/')}/oauth/callback"
    enabled = env_truthy("NIMBUSWARE_OIDC_ENABLED")
    if enabled and not (issuer and client_id and redirect):
        enabled = False
    return OidcConfig(
        enabled=enabled,
        issuer=issuer,
        client_id=client_id,
        client_secret=secret,
        redirect_uri=redirect,
    )


def oidc_admin_groups() -> frozenset[str]:
    raw = env_str("NIMBUSWARE_OIDC_ADMIN_GROUPS").strip()
    if not raw:
        return frozenset()
    return frozenset(g.strip() for g in raw.split(",") if g.strip())


def resolve_console_role_from_groups(groups: list[str] | tuple[str, ...]) -> str:
    admin_groups = oidc_admin_groups()
    if not admin_groups:
        return "admin"
    normalized = {g.strip() for g in groups if g.strip()}
    if normalized & admin_groups:
        return "admin"
    return "readonly"


def oidc_required_for_console() -> bool:
    try:
        from nimbusware_env.edition import is_enterprise

        if not is_enterprise():
            return False
    except ImportError:
        return False
    return load_oidc_config().login_ready()
