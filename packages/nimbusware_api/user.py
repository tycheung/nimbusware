from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from nimbusware_api.errors import problem
from nimbusware_env.admin_token import is_loopback_host, nimbusware_admin_token
from nimbusware_env.edition import is_enterprise
from nimbusware_env.env_flags import env_str
from nimbusware_iam.context import get_auth_context
from nimbusware_iam.scopes import has_maker_user


def _api_bind_host() -> str:
    return env_str("NIMBUSWARE_API_HOST").strip() or "127.0.0.1"


def require_user_access(
    x_nimbusware_admin_token: str | None = Header(
        default=None,
        alias="X-Nimbusware-Admin-Token",
    ),
) -> None:
    if is_enterprise():
        ctx = get_auth_context()
        if ctx is None or not has_maker_user(ctx.api_scopes):
            raise HTTPException(
                status_code=403,
                detail=problem(
                    "forbidden",
                    "API key lacks maker_user scope",
                    details={"required_scope": "maker_user"},
                ),
            )
        return

    if is_loopback_host(_api_bind_host()):
        return

    secret = nimbusware_admin_token()
    if x_nimbusware_admin_token and x_nimbusware_admin_token == secret:
        return
    raise HTTPException(
        status_code=401,
        detail=problem(
            "unauthorized",
            "missing or invalid X-Nimbusware-Admin-Token "
            "(required when API is bound to a non-loopback host)",
        ),
    )


UserDep = Annotated[None, Depends(require_user_access)]
