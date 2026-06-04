from __future__ import annotations

from nimbusware_env.admin_token import nimbusware_admin_token


def verify_admin_token(token: str) -> bool:
    return bool(token) and token == nimbusware_admin_token()


def require_admin_session() -> None:
    raise RuntimeError("Admin gate is handled in the web console at /v1/admin/app/.")
