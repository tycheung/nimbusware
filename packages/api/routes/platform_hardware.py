from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import OrchDep, StoreDep
from api.errors import problem
from env.edition import is_enterprise
from hw.audit import append_hardware_profile_detected_event
from hw.cache import get_cached_profile, rescan_hardware
from hw.fit import rank_models
from hw.fleet_hardware import probe_fleet_hardware_hosts
from hw.governor import governor_for_profile
from hw.probe import probe_hardware
from hw.profile import profile_from_probe

router = APIRouter(tags=["platform"])


class HardwareRescanBody(BaseModel):
    emit_event: bool = Field(
        default=False,
        description="Append hardware.profile.detected to the event store when true",
    )
    run_id: UUID | None = Field(
        default=None,
        description="Run to attach the hardware.profile.detected event (required when emit_event)",
    )


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


@router.post("/platform/hardware/fleet/rescan")
def post_platform_hardware_fleet_rescan() -> dict[str, Any]:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_only",
                "Fleet hardware rescan requires Enterprise edition.",
            ),
        )
    from hw.fleet_hardware import rescan_fleet_hardware_hosts

    return rescan_fleet_hardware_hosts()
