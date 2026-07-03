from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import OrchDep
from api.errors import problem
from orchestrator.autopilot_profiles import resolve_autopilot_profile
from orchestrator.enforcement_profiles import resolve_enforcement_profile
from orchestrator.user_autopilot_profiles import (
    load_user_autopilot_profiles,
    upsert_user_autopilot_profile,
)
from orchestrator.user_enforcement_profiles import (
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


@router.get("/autopilot/presets/{level}")
def get_autopilot_preset(level: int) -> dict[str, Any]:
    profile = resolve_autopilot_profile(level=level)
    return {
        "level": profile.level,
        "name": profile.name,
        "checkpoints": sorted(profile.checkpoints),
        "custom": profile.custom,
    }


@router.get("/platform/autopilot/user-profiles")
def get_user_autopilot_profiles(orch: OrchDep) -> dict[str, Any]:
    profiles = load_user_autopilot_profiles(orch.repo_root)
    return {
        "profiles": [p.to_dict() for p in profiles.values()],
    }


@router.put("/platform/autopilot/user-profiles/{profile_id}")
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


@router.get("/enforcement/presets/{level}")
def get_enforcement_preset(level: int) -> dict[str, Any]:
    profile = resolve_enforcement_profile(level=level)
    return profile.to_dict()


@router.get("/platform/enforcement/user-profiles")
def get_user_enforcement_profiles(orch: OrchDep) -> dict[str, Any]:
    profiles = load_user_enforcement_profiles(orch.repo_root)
    return {
        "profiles": [p.to_dict() for p in profiles.values()],
    }


@router.put("/platform/enforcement/user-profiles/{profile_id}")
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
