from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from nimbusware_api.errors import problem
from nimbusware_env.edition import is_enterprise
from nimbusware_iam.context import get_auth_context
from nimbusware_iam.scopes import has_maker_user


def require_user_access() -> None:
    if not is_enterprise():
        return
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


UserDep = Annotated[None, Depends(require_user_access)]
