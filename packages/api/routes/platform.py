from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import OptimizerWeightsStoreDep, OrchDep, StoreDep
from api.errors import problem
from api.routes.auth import AuthUserDep
from api.routes.platform_deploy import router as deploy_router
from api.routes.platform_discipline_profile import router as discipline_profile_router
from api.routes.platform_hardware import router as hardware_router
from api.routes.platform_model_routing import router as model_routing_router
from api.routes.platform_operator_profiles import router as operator_profiles_router
from api.routes.platform_user_profiles import router as user_profiles_router
from api.user import maker_user_id_str
from config.collab_settings_store import save_persisted_collab_enabled
from env import find_repo_root
from env.collab_runtime import collab_settings_snapshot, set_runtime_collab_enabled
from env.edition import edition_manifest, enterprise_compose_profiles
from maker.collab_disciplines import list_disciplines
from maker.collab_invite_templates import list_invite_templates
from maker.consumer_precommit_install import install_workspace_precommit
from maker.consumer_test_scaffold import scaffold_consumer_tests
from maker.onboarding import is_onboarded_server, mark_onboarded_server
from maker.playwright_bootstrap import (
    playwright_bootstrap_status,
    run_playwright_bootstrap,
)
from maker.readiness import build_platform_readiness
from maker.workspace_readiness import assess_workspace_readiness
from orchestrator.critic_pack_resolve import list_industry_critic_packs
from orchestrator.user_operator_profiles import (
    load_user_industry_critic_pack_ids,
    save_user_industry_critic_pack_ids,
)

router = APIRouter(tags=["platform"])
router.include_router(hardware_router)
router.include_router(user_profiles_router)
router.include_router(operator_profiles_router)
router.include_router(discipline_profile_router)
router.include_router(deploy_router)
router.include_router(model_routing_router)


class OptimizerWeightsBody(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)


class WorkspacePathBody(BaseModel):
    workspace_path: str = Field(min_length=1, max_length=2000)


class SafeCodingPreferencesBody(BaseModel):
    industry_critic_pack_ids: list[str] = Field(default_factory=list)


class CollabSettingsBody(BaseModel):
    collab_enabled: bool


def _require_individual_collab_owner(request: Request, user: AuthUserDep) -> str:
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    if not uid:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    edition = edition_manifest()
    if str(edition.get("edition") or "").lower() == "enterprise":
        raise HTTPException(
            status_code=403,
            detail=problem("forbidden", "collab settings are managed via enterprise policy"),
        )
    return uid


@router.get("/platform/collab-disciplines")
def get_collab_disciplines(orch: OrchDep) -> dict[str, Any]:
    return {"disciplines": list_disciplines(repo_root=orch.repo_root)}


@router.get("/platform/invite-templates")
def get_invite_templates(orch: OrchDep) -> dict[str, Any]:
    return {"templates": list_invite_templates(repo_root=orch.repo_root)}


@router.get("/platform/collab-settings")
def get_collab_settings(request: Request, user: AuthUserDep) -> dict[str, Any]:
    _require_individual_collab_owner(request, user)
    return collab_settings_snapshot()


@router.put("/platform/collab-settings")
def put_collab_settings(
    body: CollabSettingsBody,
    request: Request,
    user: AuthUserDep,
) -> dict[str, Any]:
    _require_individual_collab_owner(request, user)
    set_runtime_collab_enabled(body.collab_enabled)
    save_persisted_collab_enabled(body.collab_enabled, repo_root=find_repo_root())
    return collab_settings_snapshot()


@router.post("/platform/workspace-scaffold")
def post_workspace_scaffold(body: WorkspacePathBody, orch: OrchDep) -> dict[str, Any]:
    try:
        return scaffold_consumer_tests(Path(body.workspace_path.strip() or orch.repo_root))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.post("/platform/workspace-precommit")
def post_workspace_precommit(body: WorkspacePathBody, orch: OrchDep) -> dict[str, Any]:
    try:
        return install_workspace_precommit(Path(body.workspace_path.strip() or orch.repo_root))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.get("/platform/edition")
def get_platform_edition() -> dict[str, Any]:
    body = edition_manifest()
    body["compose_profiles"] = enterprise_compose_profiles()
    return body


@router.get("/platform/readiness")
def get_platform_readiness(orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    return build_platform_readiness(repo_root=orch.repo_root, store=store)


@router.get("/platform/fleet-governance")
def get_platform_fleet_governance(
    archetype: str = "",
    tenant_slug: str = "",
) -> dict[str, Any]:
    from maker.fleet_governance_summary import fleet_governance_summary

    return fleet_governance_summary(
        archetype=archetype.strip() or None,
        tenant_slug=tenant_slug.strip() or None,
    )


@router.get("/platform/workspace-readiness")
def get_workspace_readiness(
    workspace_path: str,
    orch: OrchDep,
) -> dict[str, Any]:
    return assess_workspace_readiness(Path(workspace_path.strip() or orch.repo_root))


@router.get("/platform/playwright-bootstrap")
def get_playwright_bootstrap() -> dict[str, Any]:
    return playwright_bootstrap_status()


@router.post("/platform/playwright-bootstrap")
def post_playwright_bootstrap() -> dict[str, Any]:
    return run_playwright_bootstrap()


@router.get("/platform/onboarding")
def get_platform_onboarding() -> dict[str, Any]:
    return {"onboarded": is_onboarded_server()}


@router.post("/platform/onboarding")
def post_platform_onboarding() -> dict[str, Any]:
    mark_onboarded_server()
    return {"onboarded": True}


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


@router.get("/platform/industry-critic-packs")
def get_industry_critic_packs(orch: OrchDep) -> dict[str, Any]:
    return {
        "packs": list_industry_critic_packs(
            orch.repo_root,
            config_materializer=orch.config_materializer,
        ),
    }


@router.get("/platform/safe-coding-preferences")
def get_safe_coding_preferences(
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
    return {
        "user_id": uid,
        "industry_critic_pack_ids": load_user_industry_critic_pack_ids(
            uid, repo_root=orch.repo_root
        ),
    }


@router.put("/platform/safe-coding-preferences")
def put_safe_coding_preferences(
    body: SafeCodingPreferencesBody,
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
    return save_user_industry_critic_pack_ids(
        uid,
        body.industry_critic_pack_ids,
        repo_root=orch.repo_root,
    )
