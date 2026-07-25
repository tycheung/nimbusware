from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import OrchDep
from api.errors import problem
from api.routes.auth import AuthUserDep
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from api.user import maker_user_id_str
from orchestrator.profiles.user_operator_profiles import (
    load_user_operator_profiles,
    save_user_operator_profiles,
)

router = APIRouter(tags=["platform"])


class OperatorProfilesBody(BaseModel):
    autopilot_profile_id: str | None = Field(default=None, max_length=120)
    enforcement_profile_id: str | None = Field(default=None, max_length=120)


class OperatorProfilesResponse(BaseModel):
    """GET/PUT /platform/operator-profiles (`sak483-g`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/platform/operator-profiles",
    response_model=OperatorProfilesResponse,
    response_model_exclude_none=True,
    summary="Operator profiles GET (`sak483-g`)",
    responses=long_tail_json_openapi_responses(),  # sak501-i
)
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


@router.put(
    "/platform/operator-profiles",
    response_model=OperatorProfilesResponse,
    response_model_exclude_none=True,
    summary="Operator profiles PUT (`sak483-g`)",
    responses=with_long_tail_peel_503(),  # sak516-c
)
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
