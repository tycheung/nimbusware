from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import OrchDep, StoreDep
from api.errors import problem
from api.routes.platform_model_routing import PlatformCapacityResponse
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import capacity_json_openapi_responses
from env.edition import is_enterprise
from hw.audit import append_hardware_profile_detected_event
from hw.cache import rescan_hardware
from hw.fit import rank_models
from hw.fleet_hardware import probe_fleet_hardware_hosts
from hw.governor import governor_for_profile, governor_from_metadata
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


def _hardware_response(
    orch: OrchDep,
    *,
    remote_host: str | None,
    binding_id: str | None = None,
) -> dict[str, Any]:
    if remote_host and remote_host.strip():
        # sak446-d: remote SSH probe is a local CAPACITY path — refuse under peel.
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import refuse_legacy

        if broker_capacity_enabled():
            refuse_legacy(
                "remote_host SSH probe unavailable under NIMBUSWARE_BROKER_CAPACITY=1|2; "
                "use SwissArmyNoife /v1/sak/capacity"
            )
        raw = probe_hardware(remote_host=remote_host.strip())
        profile = profile_from_probe(raw)
        governor = governor_for_profile(profile)
        gov_meta = {**governor.to_metadata(), "capacity_source": "local"}
        capacity_source = "local"
    else:
        from orchestrator._pipeline.resource_governor_resolve import resolve_resource_governor

        profile, gov_meta = resolve_resource_governor()
        capacity_source = str(gov_meta.get("capacity_source") or "local")
        # sak445-h: only upgrade local→broker when platform is explicitly broker-sourced
        # (do not treat ``fake`` as broker — avoids capacity_source masquerade).
        platform = str(getattr(profile, "platform", "") or "")
        if capacity_source == "local" and (
            platform.startswith("broker") or platform == "broker_capacity"
        ):
            capacity_source = "broker"
            gov_meta = {**gov_meta, "capacity_source": "broker"}
        governor = governor_from_metadata(gov_meta) or governor_for_profile(profile)

    ranked = rank_models(orch.repo_root, profile, limit=20)
    fit_via = "local"
    if binding_id and binding_id.strip():
        from broker_client.flags import broker_capacity_enabled

        try:
            fit_ranked = rank_models(
                orch.repo_root,
                profile,
                limit=20,
                binding_id=binding_id.strip(),
                candidates=list(ranked) if ranked else [{"tag": "default"}],
            )
            if fit_ranked:
                ranked = fit_ranked
                fit_via = "broker"
        except RuntimeError:
            # sak490-d: binding fit peel miss re-raises (no local ranked fallback).
            raise
        except Exception as exc:
            if broker_capacity_enabled():
                raise RuntimeError(
                    f"broker_miss: platform_hardware binding fit: {exc}"
                ) from exc
    body: dict[str, Any] = {
        "profile": profile.model_dump_public(),
        "resource_governor": dict(gov_meta),
        "models_ranked": ranked[:20],
        "capacity_source": capacity_source,
        "fit_via": fit_via,
    }
    if binding_id and binding_id.strip():
        body["binding_id"] = binding_id.strip()
    if remote_host and remote_host.strip():
        body["remote_host"] = remote_host.strip()
    # Stash governor for callers that need the dataclass (rescan emit).
    body["_governor"] = governor
    return body


@router.get(
    "/platform/hardware",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Platform hardware profile (CAPACITY peel-aware; sak443-f / sak444-e)",
    responses=capacity_json_openapi_responses(),  # sak508-i
)
def get_platform_hardware(
    orch: OrchDep,
    remote_host: str | None = Query(default=None, max_length=256),
    binding_id: str | None = Query(default=None, max_length=200),
) -> dict[str, Any]:
    try:
        body = _hardware_response(orch, remote_host=remote_host, binding_id=binding_id)
        body.pop("_governor", None)
        return body
    except Exception as exc:  # noqa: BLE001 — sak441-c: CAPACITY=1 structured miss
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_hardware",
                miss_extra={"binding_id": binding_id} if binding_id else None,
            )
        raise


@router.post(
    "/platform/hardware/rescan",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Rescan platform hardware (CAPACITY peel-aware; sak444-e)",
    responses=capacity_json_openapi_responses(),  # sak508-i
)
def post_platform_hardware_rescan(
    orch: OrchDep,
    store: StoreDep,
    body: HardwareRescanBody | None = None,
    remote_host: str | None = Query(default=None, max_length=256),
) -> dict[str, Any]:
    try:
        if remote_host and remote_host.strip():
            out = _hardware_response(orch, remote_host=remote_host)
            out.pop("_governor", None)
            return out
        # Fresh broker/local profile, then same resolve path as GET (`sak420-f`).
        rescan_hardware()
        out = _hardware_response(orch, remote_host=None)
        governor = out.pop("_governor", None)
        from hw.profile import HardwareProfile

        profile = HardwareProfile.model_validate(out["profile"])
        if governor is None:
            governor = governor_for_profile(profile)
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
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — sak441-c
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(exc, feature="platform_hardware_rescan")
        raise


@router.get(
    "/platform/hardware/fleet",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Fleet hardware aggregate (CAPACITY peel-aware; sak444-e)",
    responses=capacity_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak509-a
)
def get_platform_hardware_fleet() -> dict[str, Any]:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_only",
                "Fleet hardware aggregate requires Enterprise edition.",
            ),
        )
    try:
        return probe_fleet_hardware_hosts()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — sak442-a
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_hardware_fleet",
                miss_extra={"hosts": []},
            )
        raise


@router.post(
    "/platform/hardware/fleet/rescan",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Rescan fleet hardware (CAPACITY peel-aware; sak444-e)",
    responses=capacity_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak509-a
)
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

    try:
        return rescan_fleet_hardware_hosts()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — sak442-a
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_hardware_fleet_rescan",
                miss_extra={"hosts": []},
            )
        raise
