from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from nimbusware_api.errors import problem
from nimbusware_env.admin_token import nimbusware_admin_token


def require_admin_token(
    x_nimbusware_admin_token: str | None = Header(
        default=None,
        alias="X-Nimbusware-Admin-Token",
    ),
) -> None:
    secret = nimbusware_admin_token()
    if not x_nimbusware_admin_token or x_nimbusware_admin_token != secret:
        raise HTTPException(
            status_code=401,
            detail=problem(
                "unauthorized",
                "missing or invalid X-Nimbusware-Admin-Token",
            ),
        )


AdminDep = Annotated[None, Depends(require_admin_token)]
