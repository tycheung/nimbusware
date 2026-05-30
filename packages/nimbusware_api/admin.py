from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from nimbusware_api.errors import problem
from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_env.edition import is_enterprise
from nimbusware_iam.context import get_auth_context
from nimbusware_iam.scopes import has_maker_admin


def require_admin_token(
    x_nimbusware_admin_token: str | None = Header(
        default=None,
        alias="X-Nimbusware-Admin-Token",
    ),
) -> None:
    secret = nimbusware_admin_token()
    token_ok = bool(x_nimbusware_admin_token and x_nimbusware_admin_token == secret)
    if is_enterprise():
        ctx = get_auth_context()
        if ctx is not None:
            if not has_maker_admin(ctx.api_scopes):
                raise HTTPException(
                    status_code=403,
                    detail=problem(
                        "forbidden",
                        "API key lacks maker_admin scope",
                        details={"required_scope": "maker_admin"},
                    ),
                )
            return
        if token_ok:
            return
        raise HTTPException(
            status_code=401,
            detail=problem(
                "unauthorized",
                "missing or invalid admin credentials",
            ),
        )
    if not token_ok:
        raise HTTPException(
            status_code=401,
            detail=problem(
                "unauthorized",
                "missing or invalid X-Nimbusware-Admin-Token",
            ),
        )


AdminDep = Annotated[None, Depends(require_admin_token)]
