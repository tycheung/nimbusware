from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_env.edition import edition_manifest, enterprise_compose_profiles, is_enterprise
from nimbusware_hw.audit import append_hardware_profile_detected_event
from nimbusware_hw.cache import get_cached_profile, rescan_hardware
from nimbusware_hw.fit import rank_models
from nimbusware_hw.fleet_hardware import probe_fleet_hardware_hosts
from nimbusware_hw.governor import governor_for_profile
from nimbusware_hw.probe import probe_hardware
from nimbusware_hw.profile import profile_from_probe
from nimbusware_maker.onboarding import is_onboarded_server, mark_onboarded_server
from nimbusware_maker.readiness import build_platform_readiness
from nimbusware_orchestrator.autopilot_profiles import resolve_autopilot_profile
from nimbusware_orchestrator.user_autopilot_profiles import (
    load_user_autopilot_profiles,
    upsert_user_autopilot_profile,
)

router = APIRouter(tags=["platform"])


class UserAutopilotProfileBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(ge=0, le=10, default=5)
    checkpoints: list[str] = Field(default_factory=list)


class HardwareRescanBody(BaseModel):
    emit_event: bool = Field(
        default=False,
        description="Append hardware.profile.detected to the event store when true",
    )
    run_id: UUID | None = Field(
        default=None,
        description="Run to attach the hardware.profile.detected event (required when emit_event)",
    )


@router.get("/platform/edition")
def get_platform_edition() -> dict[str, Any]:
    body = edition_manifest()
    body["compose_profiles"] = enterprise_compose_profiles()
    return body


@router.get("/platform/readiness")
def get_platform_readiness(orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    return build_platform_readiness(repo_root=orch.repo_root, store=store)


def _hardware_response(orch: OrchDep, *, remote_host: str | None) -> dict[str, Any]:
    if remote_host and remote_host.strip():
        raw = probe_hardware(remote_host=remote_host.strip())
        profile = profile_from_probe(raw)
    else:
        profile = get_cached_profile()
    governor = governor_for_profile(profile)
    ranked = rank_models(orch.repo_root, profile, limit=20)
    body: dict[str, Any] = {
        "profile": profile.model_dump_public(),
        "resource_governor": governor.to_metadata(),
        "models_ranked": ranked[:20],
    }
    if remote_host and remote_host.strip():
        body["remote_host"] = remote_host.strip()
    return body


@router.get("/platform/hardware")
def get_platform_hardware(
    orch: OrchDep,
    remote_host: str | None = Query(default=None, max_length=256),
) -> dict[str, Any]:
    return _hardware_response(orch, remote_host=remote_host)


@router.post("/platform/hardware/rescan")
def post_platform_hardware_rescan(
    orch: OrchDep,
    store: StoreDep,
    body: HardwareRescanBody | None = None,
    remote_host: str | None = Query(default=None, max_length=256),
) -> dict[str, Any]:
    if remote_host and remote_host.strip():
        return _hardware_response(orch, remote_host=remote_host)
    profile = rescan_hardware()
    governor = governor_for_profile(profile)
    ranked = rank_models(orch.repo_root, profile, limit=20)
    out: dict[str, Any] = {
        "profile": profile.model_dump_public(),
        "resource_governor": governor.to_metadata(),
        "models_ranked": ranked[:20],
    }
    req = body or HardwareRescanBody()
    if req.emit_event and req.run_id is None:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "run_id_required",
                "run_id is required when emit_event is true",
            ),
        )
    if req.emit_event and req.run_id is not None:
        store_seq = append_hardware_profile_detected_event(
            store,
            run_id=req.run_id,
            profile=profile,
            governor=governor,
        )
        out["event_emitted"] = True
        out["store_seq"] = store_seq
    return out


@router.get("/platform/hardware/fleet")
def get_platform_hardware_fleet() -> dict[str, Any]:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_only",
                "Fleet hardware aggregate requires Enterprise edition.",
            ),
        )
    return probe_fleet_hardware_hosts()


@router.get("/platform/onboarding")
def get_platform_onboarding() -> dict[str, Any]:
    return {"onboarded": is_onboarded_server()}


@router.post("/platform/onboarding")
def post_platform_onboarding() -> dict[str, Any]:
    mark_onboarded_server()
    return {"onboarded": True}


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
