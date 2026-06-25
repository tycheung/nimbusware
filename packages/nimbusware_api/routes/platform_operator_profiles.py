from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.user import maker_user_id_str
from nimbusware_orchestrator.user_operator_profiles import (
    load_user_operator_profiles,
    save_user_operator_profiles,
)

router = APIRouter(tags=["platform"])


class OperatorProfilesBody(BaseModel):
    autopilot_profile_id: str | None = Field(default=None, max_length=120)
    enforcement_profile_id: str | None = Field(default=None, max_length=120)


@router.get("/platform/operator-profiles")
def get_operator_profiles(
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    return load_user_operator_profiles(uid, repo_root=orch.repo_root)


@router.put("/platform/operator-profiles")
def put_operator_profiles(
    body: OperatorProfilesBody,
    request: Request,
    orch: OrchDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    try:
        return save_user_operator_profiles(
            uid,
            autopilot_profile_id=body.autopilot_profile_id,
            enforcement_profile_id=body.enforcement_profile_id,
            repo_root=orch.repo_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
