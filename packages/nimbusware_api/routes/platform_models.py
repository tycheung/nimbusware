from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_422, PROBLEM_RESPONSE_500
from nimbusware_config.keys import KEY_MODEL_ROUTING, NS_POLICY
from nimbusware_config.store import PostgresConfigStore
from nimbusware_hw.cache import get_cached_profile, rescan_hardware
from nimbusware_hw.fit import rank_models
from nimbusware_hw.governor import governor_for_profile
from nimbusware_hw.ollama_presets import PRESET_NAMES
from nimbusware_maker.readiness import build_platform_readiness

router = APIRouter(tags=["platform"])


class ApplyPresetBody(BaseModel):
    model_id: str = Field(min_length=1)
    preset: Literal["quality", "balanced", "speed"] = "balanced"
    target: Literal["model-routing", "run_defaults"] = "model-routing"


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
            detail=problem("model_not_found", "model not in allowlist", details={"model_id": body.model_id}),
        )
    presets = row.get("presets") if isinstance(row.get("presets"), dict) else {}
    chosen = presets.get(body.preset) if isinstance(presets, dict) else {}
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
    }


@router.get("/platform/models/dependencies")
def get_model_dependencies(orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    readiness = build_platform_readiness(repo_root=orch.repo_root, store=store)
    checks = readiness.get("checks") if isinstance(readiness.get("checks"), dict) else {}
    ollama = checks.get("ollama") if isinstance(checks.get("ollama"), dict) else {}
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
