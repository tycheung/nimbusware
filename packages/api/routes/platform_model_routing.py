from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agent_core.mapping import mapping_or_empty
from api.deps import OrchDep, StoreDep
from api.errors import problem
from config.keys import KEY_MODEL_ROUTING, NS_POLICY
from config.store import PostgresConfigStore
from hw.cache import get_cached_profile
from hw.catalog_sync import catalog_info_from_path
from hw.fit import rank_models
from hw.ollama_presets import PRESET_NAMES
from maker.readiness.platform import build_platform_readiness
from orchestrator.routing.presets import (
    apply_routing_preset,
    list_routing_preset_summaries,
)
from orchestrator.stage_provider_routing import probe_cloud_runtime

router = APIRouter(tags=["platform"])


class ApplyPresetBody(BaseModel):
    model_id: str = Field(min_length=1)
    preset: Literal["quality", "balanced", "speed"] = "balanced"
    target: Literal["model-routing", "run_defaults"] = "model-routing"


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
    routing = load_routing_yaml(orch.repo_root / "configs" / "model-routing.yaml")
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
    content = load_routing_yaml(routing_path)
    from env.env_flags import env_str

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
