from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request

from nimbusware_api.errors import problem
from nimbusware_auth.models import UserRecord
from nimbusware_auth.session_cookie import user_id_from_request
from nimbusware_env.env_flags import nimbusware_collab_enabled


def require_collab_enabled() -> None:
    if not nimbusware_collab_enabled():
        raise HTTPException(
            status_code=403,
            detail=problem("collab_disabled", "collaborative chat is disabled"),
        )


def actor_user_id(request: Request, user: UserRecord | None) -> UUID:
    if user is not None:
        return user.user_id
    uid = user_id_from_request(request)
    if uid is not None:
        return uid
    raise HTTPException(
        status_code=401,
        detail=problem("unauthorized", "sign in required"),
    )
