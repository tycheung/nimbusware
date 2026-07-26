from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agent_core.mapping import mapping_or_empty
from api.deps import OrchDep, StoreDep
from api.errors import problem
from api.schemas.peel_responses import capacity_json_openapi_responses, with_long_tail_peel_503
from config.keys import KEY_MODEL_ROUTING, NS_POLICY
from config.store import PostgresConfigStore
from hw.cache import get_cached_profile
from hw.catalog_sync import catalog_info_from_path
from hw.fit import rank_models
from hw.ollama_presets import PRESET_NAMES
from maker.readiness.platform import build_platform_readiness
from orchestrator.model_routing.presets import (
    apply_routing_preset,
    list_routing_preset_summaries,
)
from orchestrator.provider_routing_facade import probe_cloud_runtime

router = APIRouter(tags=["platform"])


class ApplyPresetBody(BaseModel):
    model_id: str = Field(min_length=1)
    preset: Literal["quality", "balanced", "speed"] = "balanced"
    target: Literal["model-routing", "run_defaults"] = "model-routing"


class PlatformCapacityResponse(BaseModel):
    """CAPACITY peel-aware platform response (`sak443-f` / `sak444-e` / `sak445-b`)."""

    model_config = {"protected_namespaces": ()}

    via: str | None = None
    capacity_source: str | None = None
    fit_via: str | None = None
    status: str | None = None
    error: str | None = None
    feature: str | None = None
    models: list[dict[str, Any]] | None = None
    models_ranked: list[dict[str, Any]] | None = None
    profile_tier: str | None = None
    use_case: str | None = None
    gpu_only: bool | None = None
    model_id: str | None = None
    preset: str | None = None
    ollama_tag: str | None = None
    materialize_hint: str | None = None
    preset_applied: dict[str, Any] | None = None
    profile: dict[str, Any] | None = None
    resource_governor: dict[str, Any] | None = None
    hosts: list[dict[str, Any]] | None = None
    event_emitted: bool | None = None
    store_seq: int | None = None
    binding_id: str | None = None
    preset_id: str | None = None
    remote_host: str | None = None
    label: str | None = None
    routing_preset_id: str | None = None
    cloud_runtime: dict[str, Any] | None = None
    stage_providers: dict[str, Any] | None = None
    cloud_preflight: dict[str, Any] | None = None
    cloud_enabled: bool | None = None


class CatalogInfoResponse(BaseModel):
    """GET /platform/models/catalog-info (`sak445-c`)."""

    model_config = {"protected_namespaces": ()}

    model_count: int | None = None
    version: str | int | None = None
    updated_at: str | None = None
    source: str | None = None
    path: str | None = None


class RoutingPresetsListResponse(BaseModel):
    """GET /platform/routing-presets (`sak445-c`)."""

    presets: list[dict[str, Any]] = Field(default_factory=list)
    active_preset_id: str | None = None
    cloud_preflight: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ModelDependenciesResponse(BaseModel):
    """GET /platform/models/dependencies (`sak445-c`)."""

    ollama_reachable: bool | None = None
    ollama_message: str | None = None
    docker_gpu_warning: str | None = None
    checks: dict[str, Any] | None = None
    via: str | None = None
    capacity_source: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


class ApplyRoutingPresetBody(BaseModel):
    preset_id: str = Field(min_length=1, max_length=80)


def load_routing_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "models": {}}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1, "models": {}}


def persist_routing(repo_root: Path, content: dict[str, Any]) -> None:
    from env.env_flags import env_str

    conn = env_str("NIMBUSWARE_DATABASE_URL")
    if conn:
        store = PostgresConfigStore(conn)
        store.upsert(NS_POLICY, KEY_MODEL_ROUTING, content)
    else:
        path = repo_root / "configs" / "model-routing.yaml"
        path.write_text(yaml.dump(content, sort_keys=False), encoding="utf-8")


@router.get(
    "/platform/models/catalog-info",
    response_model=CatalogInfoResponse,
    response_model_exclude_none=True,
    summary="Model catalog info (`sak445-c`)",
    responses=with_long_tail_peel_503(),  # sak509-b
)
def get_model_catalog_info(orch: OrchDep) -> dict[str, Any]:
    path = orch.repo_root / "configs" / "hardware" / "model_catalog.json"
    return catalog_info_from_path(path, source="bundled")


@router.get(
    "/platform/models/ranked",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Rank models for hardware (CAPACITY peel-aware; sak443-f)",
    responses=capacity_json_openapi_responses(),  # sak509-b
)
def get_models_ranked(
    orch: OrchDep,
    use_case: str = Query(default="coding"),
    gpu_only: bool = Query(default=False),
    gpu_group_index: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    # sak436-g / sak442-c: under CAPACITY peel, miss → structured body (not 500).
    try:
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
    except Exception as exc:  # noqa: BLE001 — sak441-c / sak490-d: CAPACITY=1 miss / CAPACITY=2 503
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_models_ranked",
                miss_extra={
                    "use_case": use_case,
                    "gpu_only": gpu_only,
                    "models": [],
                    "profile_tier": None,
                },
            )
        raise


@router.post(
    "/platform/models/apply-preset",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Apply model preset (CAPACITY peel-aware; sak443-a/f)",
    responses=capacity_json_openapi_responses(),  # sak509-c
)
def post_apply_preset(orch: OrchDep, body: ApplyPresetBody) -> dict[str, Any]:
    if body.preset not in PRESET_NAMES:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_preset", f"preset must be one of {PRESET_NAMES}"),
        )
    try:
        profile = get_cached_profile()
        ranked = rank_models(orch.repo_root, profile, limit=100)
        row = next((r for r in ranked if r.get("model_id") == body.model_id), None)
        if row is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "model_not_found",
                    "model not in allowlist",
                    details={"model_id": body.model_id},
                ),
            )
        presets = mapping_or_empty(row.get("presets"))
        chosen = mapping_or_empty(presets.get(body.preset))
        tag = str(chosen.get("ollama_tag") or body.model_id)
        routing_path = orch.repo_root / "configs" / "model-routing.yaml"
        content = load_routing_yaml(routing_path)
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
        persist_routing(orch.repo_root, content)
        return {
            "status": "applied",
            "model_id": body.model_id,
            "preset": body.preset,
            "ollama_tag": tag,
            "materialize_hint": (
                "Run nimbusware-config materialize or restart API to reload routing"
            ),
            "preset_applied": {
                "model_id": body.model_id,
                "preset": body.preset,
                "target": body.target,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — sak443-a
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_models_apply_preset",
                miss_extra={
                    "status": "degraded",
                    "model_id": body.model_id,
                    "preset": body.preset,
                },
            )
        raise


@router.get(
    "/platform/routing-presets",
    response_model=RoutingPresetsListResponse,
    response_model_exclude_none=True,
    summary="List routing presets (`sak445-c`)",
    responses=with_long_tail_peel_503(),  # sak509-c
)
def get_routing_presets(orch: OrchDep) -> dict[str, Any]:
    presets = list_routing_preset_summaries(orch.repo_root)
    routing = load_routing_yaml(orch.repo_root / "configs" / "model-routing.yaml")
    active = str(routing.get("routing_preset_id") or "local_only")
    cloud_probe = probe_cloud_runtime(routing)
    return {
        "presets": presets,
        "active_preset_id": active,
        "cloud_preflight": cloud_probe,
    }


@router.post(
    "/platform/routing-presets/apply",
    response_model=PlatformCapacityResponse,
    response_model_exclude_none=True,
    summary="Apply routing preset (CAPACITY peel-aware; sak445-b)",
    responses=capacity_json_openapi_responses(),  # sak509-g
)
def post_apply_routing_preset(orch: OrchDep, body: ApplyRoutingPresetBody) -> dict[str, Any]:
    try:
        applied = apply_routing_preset(orch.repo_root, body.preset_id)
        routing_path = orch.repo_root / "configs" / "model-routing.yaml"
        content = load_routing_yaml(routing_path)
        from env.env_flags import env_str

        conn = env_str("NIMBUSWARE_DATABASE_URL")
        if conn:
            PostgresConfigStore(conn).upsert(NS_POLICY, KEY_MODEL_ROUTING, content)
        applied["cloud_preflight"] = probe_cloud_runtime(content)
        return applied
    except KeyError:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_routing_preset",
                "routing preset not found",
                details={"preset_id": body.preset_id},
            ),
        ) from None
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — sak444-b
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_routing_presets_apply",
                miss_extra={"preset_id": body.preset_id, "status": "degraded"},
            )
        raise


@router.get(
    "/platform/models/dependencies",
    response_model=ModelDependenciesResponse,
    response_model_exclude_none=True,
    summary="Model dependency readiness (`sak445-c`)",
    responses=capacity_json_openapi_responses(),  # sak509-g
)
def get_model_dependencies(orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    try:
        readiness = build_platform_readiness(repo_root=orch.repo_root, store=store)
        checks = mapping_or_empty(readiness.get("checks"))
        ollama = mapping_or_empty(checks.get("ollama"))
        return {
            "ollama_reachable": ollama.get("status") == "ok",
            "ollama_message": ollama.get("message"),
            "docker_gpu_warning": (
                "GPU may not be visible inside Docker; use GPU compose overlay "
                "if discrete GPU expected."
            ),
            "checks": checks,
        }
    except Exception as exc:  # noqa: BLE001 — sak447-c / sak490-d: CAPACITY=1 miss / CAPACITY=2 503
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_models_dependencies",
                miss_extra={
                    "ollama_reachable": False,
                    "checks": {},
                    "status": "degraded",
                },
            )
        raise
