from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import OrchDep
from api.errors import problem
from api.schemas.peel_responses import long_tail_json_openapi_responses, with_long_tail_peel_503
from orchestrator.profiles.autopilot_profiles import resolve_autopilot_profile
from orchestrator.profiles.enforcement_profiles import resolve_enforcement_profile
from orchestrator.profiles.user_autopilot_profiles import (
    load_user_autopilot_profiles,
    upsert_user_autopilot_profile,
)
from orchestrator.profiles.user_enforcement_profiles import (
    load_user_enforcement_profiles,
    upsert_user_enforcement_profile,
)

router = APIRouter(tags=["platform"])


class UserAutopilotProfileBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(ge=0, le=10, default=5)
    checkpoints: list[str] = Field(default_factory=list)


class UserEnforcementProfileBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(ge=0, le=10, default=5)


class AutopilotPresetResponse(BaseModel):
    """GET /autopilot/presets/{level} (`sak483-e`)."""

    model_config = {"extra": "allow"}

    level: int | None = None
    name: str | None = None
    checkpoints: list[str] | None = None
    custom: bool | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class UserAutopilotProfilesResponse(BaseModel):
    """GET /platform/autopilot/user-profiles (`sak483-e`)."""

    model_config = {"extra": "allow"}

    profiles: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class UserAutopilotProfileResponse(BaseModel):
    """PUT /platform/autopilot/user-profiles/{profile_id} (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class EnforcementPresetResponse(BaseModel):
    """GET /enforcement/presets/{level} (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class UserEnforcementProfilesResponse(BaseModel):
    """GET /platform/enforcement/user-profiles (`sak483-e`)."""

    model_config = {"extra": "allow"}

    profiles: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class UserEnforcementProfileResponse(BaseModel):
    """PUT /platform/enforcement/user-profiles/{profile_id} (`sak483-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/autopilot/presets/{level}",
    response_model=AutopilotPresetResponse,
    response_model_exclude_none=True,
    summary="Autopilot preset (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak516-b
)
def get_autopilot_preset(level: int) -> dict[str, Any]:
    profile = resolve_autopilot_profile(level=level)
    return {
        "level": profile.level,
        "name": profile.name,
        "checkpoints": sorted(profile.checkpoints),
        "custom": profile.custom,
    }


@router.get(
    "/platform/autopilot/user-profiles",
    response_model=UserAutopilotProfilesResponse,
    response_model_exclude_none=True,
    summary="User autopilot profiles GET (`sak483-e`)",
    responses=long_tail_json_openapi_responses(),  # sak501-b
)
def get_user_autopilot_profiles(orch: OrchDep) -> dict[str, Any]:
    profiles = load_user_autopilot_profiles(orch.repo_root)
    return {
        "profiles": [p.to_dict() for p in profiles.values()],
    }


@router.put(
    "/platform/autopilot/user-profiles/{profile_id}",
    response_model=UserAutopilotProfileResponse,
    response_model_exclude_none=True,
    summary="User autopilot profile PUT (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak516-g
)
def put_user_autopilot_profile(
    profile_id: str,
    body: UserAutopilotProfileBody,
    orch: OrchDep,
) -> dict[str, Any]:
    pid = profile_id.strip()
    if not pid:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_profile_id", "profile_id is required"),
        )
    entry = upsert_user_autopilot_profile(
        profile_id=pid,
        name=body.name,
        level=body.level,
        checkpoints=body.checkpoints,
        repo_root=orch.repo_root,
    )
    return entry.to_dict()


@router.get(
    "/enforcement/presets/{level}",
    response_model=EnforcementPresetResponse,
    response_model_exclude_none=True,
    summary="Enforcement preset (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak516-c
)
def get_enforcement_preset(level: int) -> dict[str, Any]:
    profile = resolve_enforcement_profile(level=level)
    return profile.to_dict()


@router.get(
    "/platform/enforcement/user-profiles",
    response_model=UserEnforcementProfilesResponse,
    response_model_exclude_none=True,
    summary="User enforcement profiles GET (`sak483-e`)",
    responses=long_tail_json_openapi_responses(),  # sak501-b
)
def get_user_enforcement_profiles(orch: OrchDep) -> dict[str, Any]:
    profiles = load_user_enforcement_profiles(orch.repo_root)
    return {
        "profiles": [p.to_dict() for p in profiles.values()],
    }


@router.put(
    "/platform/enforcement/user-profiles/{profile_id}",
    response_model=UserEnforcementProfileResponse,
    response_model_exclude_none=True,
    summary="User enforcement profile PUT (`sak483-e`)",
    responses=with_long_tail_peel_503(),  # sak516-g
)
def put_user_enforcement_profile(
    profile_id: str,
    body: UserEnforcementProfileBody,
    orch: OrchDep,
) -> dict[str, Any]:
    pid = profile_id.strip()
    if not pid:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_profile_id", "profile_id is required"),
        )
    entry = upsert_user_enforcement_profile(
        profile_id=pid,
        name=body.name,
        level=body.level,
        repo_root=orch.repo_root,
    )
    return entry.to_dict()
