"""Local-only admin gate for dangerous routes (plan §6.6)."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from hermes_api.errors import problem


def require_admin_token(
    x_hermes_admin_token: str | None = Header(
        default=None,
        alias="X-Hermes-Admin-Token",
    ),
) -> None:
    secret = os.environ.get("HERMES_ADMIN_TOKEN")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail=problem(
                "admin_token_not_configured",
                "HERMES_ADMIN_TOKEN is not configured on the server",
            ),
        )
    if not x_hermes_admin_token or x_hermes_admin_token != secret:
        raise HTTPException(
            status_code=401,
            detail=problem(
                "unauthorized",
                "missing or invalid X-Hermes-Admin-Token",
            ),
        )


AdminDep = Annotated[None, Depends(require_admin_token)]
