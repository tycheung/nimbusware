from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agent_core.mapping import mapping_or_empty
from nimbusware_api.deps import OptimizerWeightsStoreDep, OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_config.keys import KEY_MODEL_ROUTING, NS_POLICY
from nimbusware_config.store import PostgresConfigStore
from nimbusware_env.edition import edition_manifest, enterprise_compose_profiles, is_enterprise
from nimbusware_hw.audit import append_hardware_profile_detected_event
from nimbusware_hw.cache import get_cached_profile, rescan_hardware
from nimbusware_hw.catalog_sync import catalog_info_from_path
from nimbusware_hw.fit import rank_models
from nimbusware_hw.fleet_hardware import probe_fleet_hardware_hosts
from nimbusware_hw.governor import governor_for_profile
from nimbusware_hw.ollama_presets import PRESET_NAMES
from nimbusware_hw.probe import probe_hardware
from nimbusware_hw.profile import profile_from_probe
from nimbusware_maker.onboarding import is_onboarded_server, mark_onboarded_server
from nimbusware_maker.readiness import build_platform_readiness
from nimbusware_orchestrator.autopilot_profiles import resolve_autopilot_profile
from nimbusware_orchestrator.enforcement_profiles import resolve_enforcement_profile
from nimbusware_orchestrator.routing_presets import (
    apply_routing_preset,
    list_routing_preset_summaries,
)
from nimbusware_orchestrator.stage_provider_routing import probe_cloud_runtime
from nimbusware_orchestrator.user_autopilot_profiles import (
    load_user_autopilot_profiles,
    upsert_user_autopilot_profile,
)
from nimbusware_orchestrator.user_enforcement_profiles import (
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
    from nimbusware_hw.fleet_hardware import rescan_fleet_hardware_hosts

    return rescan_fleet_hardware_hosts()


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


class ApplyPresetBody(BaseModel):
    model_id: str = Field(min_length=1)
    preset: Literal["quality", "balanced", "speed"] = "balanced"
    target: Literal["model-routing", "run_defaults"] = "model-routing"


class ApplyRoutingPresetBody(BaseModel):
    preset_id: str = Field(min_length=1, max_length=80)


@router.get("/platform/models/catalog-info")
def get_model_catalog_info(orch: OrchDep) -> dict[str, Any]:
    path = orch.repo_root / "configs" / "hardware" / "model_catalog.json"
    return catalog_info_from_path(path, source="bundled")


@router.get("/platform/models/ranked")
def get_models_ranked(
    orch: OrchDep,
    use_case: str = Query(default="coding"),
    gpu_only: bool = Query(default=False),
    gpu_group_index: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    profile = get_cached_profile()
    ranked = rank_models(
        orch.repo_root,
        profile,
        use_case=use_case,
        gpu_only=gpu_only,
        gpu_group_index=gpu_group_index,
        limit=limit,
    )
    return {
        "use_case": use_case,
        "gpu_only": gpu_only,
        "models": ranked,
        "profile_tier": profile.tier,
    }


@router.post("/platform/models/apply-preset")
def post_apply_preset(orch: OrchDep, body: ApplyPresetBody) -> dict[str, Any]:
    if body.preset not in PRESET_NAMES:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_preset", f"preset must be one of {PRESET_NAMES}"),
        )
    profile = get_cached_profile()
    ranked = rank_models(orch.repo_root, profile, limit=100)
    row = next((r for r in ranked if r.get("model_id") == body.model_id), None)
    if row is None:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "model_not_found", "model not in allowlist", details={"model_id": body.model_id}
            ),
        )
    presets = mapping_or_empty(row.get("presets"))
    chosen = mapping_or_empty(presets.get(body.preset))
    tag = str(chosen.get("ollama_tag") or body.model_id)
    routing_path = orch.repo_root / "configs" / "model-routing.yaml"
    content = _load_routing_yaml(routing_path)
    models = content.setdefault("models", {})
    if not isinstance(models, dict):
        models = {}
        content["models"] = models
    models["primary"] = {
        "id": tag,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_output_tokens": int(chosen.get("num_ctx") or 4096),
    }
    _persist_routing(orch.repo_root, content)
    return {
        "status": "applied",
        "model_id": body.model_id,
        "preset": body.preset,
        "ollama_tag": tag,
        "materialize_hint": "Run nimbusware-config materialize or restart API to reload routing",
        "preset_applied": {
            "model_id": body.model_id,
            "preset": body.preset,
            "target": body.target,
        },
    }


@router.get("/platform/routing-presets")
def get_routing_presets(orch: OrchDep) -> dict[str, Any]:
    presets = list_routing_preset_summaries(orch.repo_root)
    routing = _load_routing_yaml(orch.repo_root / "configs" / "model-routing.yaml")
    active = str(routing.get("routing_preset_id") or "local_only")
    cloud_probe = probe_cloud_runtime(routing)
    return {
        "presets": presets,
        "active_preset_id": active,
        "cloud_preflight": cloud_probe,
    }


@router.post("/platform/routing-presets/apply")
def post_apply_routing_preset(orch: OrchDep, body: ApplyRoutingPresetBody) -> dict[str, Any]:
    try:
        applied = apply_routing_preset(orch.repo_root, body.preset_id)
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_routing_preset",
                "routing preset not found",
                details={"preset_id": body.preset_id},
            ),
        ) from None
    routing_path = orch.repo_root / "configs" / "model-routing.yaml"
    content = _load_routing_yaml(routing_path)
    from nimbusware_env.env_flags import env_str

    conn = env_str("NIMBUSWARE_DATABASE_URL")
    if conn:
        PostgresConfigStore(conn).upsert(NS_POLICY, KEY_MODEL_ROUTING, content)
    applied["cloud_preflight"] = probe_cloud_runtime(content)
    return applied


@router.get("/platform/models/dependencies")
def get_model_dependencies(orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    readiness = build_platform_readiness(repo_root=orch.repo_root, store=store)
    checks = mapping_or_empty(readiness.get("checks"))
    ollama = mapping_or_empty(checks.get("ollama"))
    return {
        "ollama_reachable": ollama.get("status") == "ok",
        "ollama_message": ollama.get("message"),
        "docker_gpu_warning": (
            "GPU may not be visible inside Docker; use GPU compose overlay if discrete GPU expected."
        ),
        "checks": checks,
    }


def _load_routing_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "models": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "models": {}}


def _persist_routing(repo_root: Path, content: dict[str, Any]) -> None:
    from nimbusware_env.env_flags import env_str

    conn = env_str("NIMBUSWARE_DATABASE_URL")
    if conn:
        store = PostgresConfigStore(conn)
        store.upsert(NS_POLICY, KEY_MODEL_ROUTING, content)
    else:
        path = repo_root / "configs" / "model-routing.yaml"
        path.write_text(yaml.dump(content, sort_keys=False), encoding="utf-8")


class OptimizerWeightsBody(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)


@router.get("/platform/optimizer-weights")
def get_optimizer_weights(
    user: AuthUserDep,
    weights_store: OptimizerWeightsStoreDep,
) -> dict[str, Any]:
    row = weights_store.get(user_id=user.user_id)
    return {"weights": row.weights, "updated_at": row.updated_at.isoformat()}


@router.put("/platform/optimizer-weights")
def put_optimizer_weights(
    body: OptimizerWeightsBody,
    user: AuthUserDep,
    weights_store: OptimizerWeightsStoreDep,
) -> dict[str, Any]:
    row = weights_store.put(user_id=user.user_id, weights=body.weights)
    return {"weights": row.weights, "updated_at": row.updated_at.isoformat()}
