"""Local-only admin gate for dangerous routes (plan §6.6)."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from nimbusware_api.errors import problem


def require_admin_token(
    x_nimbusware_admin_token: str | None = Header(
        default=None,
        alias="X-Nimbusware-Admin-Token",
    ),
) -> None:
    secret = os.environ.get("NIMBUSWARE_ADMIN_TOKEN")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail=problem(
                "admin_token_not_configured",
                "NIMBUSWARE_ADMIN_TOKEN is not configured on the server",
            ),
        )
    if not x_nimbusware_admin_token or x_nimbusware_admin_token != secret:
        raise HTTPException(
            status_code=401,
            detail=problem(
                "unauthorized",
                "missing or invalid X-Nimbusware-Admin-Token",
            ),
        )


AdminDep = Annotated[None, Depends(require_admin_token)]
