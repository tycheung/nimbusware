from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import OptimizerWeightsStoreDep, OrchDep, StoreDep
from api.errors import problem
from api.routes.auth import AuthUserDep
from api.schemas.openapi import PROBLEM_RESPONSE_422
from api.schemas.peel_responses import (
    capacity_json_openapi_responses,
    platform_bootstrap_json_openapi_responses,
    platform_peel_json_openapi_responses,
    with_long_tail_peel_503,
)
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
from maker.collab.disciplines import list_disciplines
from maker.collab.invite_templates import list_invite_templates
from maker.consumer_precommit_install import install_workspace_precommit
from maker.consumer_test_scaffold import scaffold_consumer_tests
from maker.onboarding import is_onboarded_server, mark_onboarded_server
from maker.playwright_bootstrap import (
    playwright_bootstrap_status,
    run_playwright_bootstrap,
)
from maker.readiness.platform import build_platform_readiness
from maker.workspace.readiness import assess_workspace_readiness
from orchestrator.critique.pack_resolve import list_industry_critic_packs
from orchestrator.profiles.user_operator_profiles import (
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


class PlatformOptimizerWeightsResponse(BaseModel):
    """GET/PUT /platform/optimizer-weights (`sak446-c`)."""

    weights: dict[str, float] = Field(default_factory=dict)
    updated_at: str | None = None


class PlatformReadinessResponse(BaseModel):
    """GET /platform/readiness (`sak447-d`)."""

    model_config = {"protected_namespaces": ()}

    status: str | None = None
    checks: dict[str, Any] | None = None
    via: str | None = None
    capacity_source: str | None = None
    error: str | None = None
    feature: str | None = None
    inference_mode_label: str | None = None
    install_profile: str | None = None
    model_hub_cta: str | None = None
    model_hub_action: str | None = None


class PlatformOnboardingResponse(BaseModel):
    """GET/POST /platform/onboarding (`sak447-d`)."""

    onboarded: bool = False


class FleetGovernanceResponse(BaseModel):
    """GET /platform/fleet-governance (`sak448-e`)."""

    setup_bundle: str | None = None
    mandatory_discovery: bool | None = None
    default_surfaces: list[str] | None = None
    surface_policy: dict[str, Any] | None = None
    enforcement_policy: dict[str, Any] | None = None
    deploy_chain_required: bool | None = None
    allowed_deploy_targets: list[str] | None = None
    discovery_required_fields: list[str] | None = None
    deploy_approval_chain: str | None = None
    allowed_stacks: dict[str, str] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class WorkspaceReadinessResponse(BaseModel):
    """GET /platform/workspace-readiness (`sak448-e`)."""

    ready: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: dict[str, Any] = Field(default_factory=dict)
    plain_summary: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class WorkspacePathBody(BaseModel):
    workspace_path: str = Field(min_length=1, max_length=2000)


class SafeCodingPreferencesBody(BaseModel):
    industry_critic_pack_ids: list[str] = Field(default_factory=list)


class WorkspaceScaffoldResponse(BaseModel):
    """POST workspace-scaffold / precommit (`sak480-d`)."""

    model_config = {"extra": "allow"}

    created: list[str] | None = None
    skipped: list[str] | None = None
    plain_summary: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class IndustryCriticPacksResponse(BaseModel):
    """GET /platform/industry-critic-packs (`sak480-d`)."""

    packs: list[dict[str, Any]] = Field(default_factory=list)
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class SafeCodingPreferencesResponse(BaseModel):
    """GET/PUT /platform/safe-coding-preferences (`sak480-d`)."""

    user_id: str | None = None
    industry_critic_pack_ids: list[str] = Field(default_factory=list)
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class CollabSettingsBody(BaseModel):
    collab_enabled: bool


class CollabDisciplinesResponse(BaseModel):
    """GET /platform/collab-disciplines (`sak449-d`)."""

    disciplines: list[Any] = Field(default_factory=list)


class InviteTemplatesResponse(BaseModel):
    """GET /platform/invite-templates (`sak449-d`)."""

    templates: list[Any] = Field(default_factory=list)


class CollabSettingsResponse(BaseModel):
    """GET/PUT /platform/collab-settings (`sak449-d`)."""

    collab_enabled: bool = False
    source: str | None = None


class PlatformEditionResponse(BaseModel):
    """GET /platform/edition (`sak449-d`)."""

    edition: str | None = None
    individual: bool | None = None
    enterprise: bool | None = None
    env_var: str | None = None
    features: dict[str, Any] | None = None
    compose_profiles: list[str] | None = None


class PlaywrightBootstrapResponse(BaseModel):
    """GET/POST /platform/playwright-bootstrap (`sak449-d`)."""

    status: str | None = None
    plain_summary: str | None = None
    error: str | None = None


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


@router.get(
    "/platform/collab-disciplines",
    response_model=CollabDisciplinesResponse,
    summary="Collab disciplines (`sak449-d`)",
    responses=platform_peel_json_openapi_responses(),  # sak496-f
)
def get_collab_disciplines(orch: OrchDep) -> dict[str, Any]:
    return {"disciplines": list_disciplines(repo_root=orch.repo_root)}


@router.get(
    "/platform/invite-templates",
    response_model=InviteTemplatesResponse,
    summary="Invite templates (`sak449-d`)",
    responses=with_long_tail_peel_503(),  # sak509-h
)
def get_invite_templates(orch: OrchDep) -> dict[str, Any]:
    return {"templates": list_invite_templates(repo_root=orch.repo_root)}


@router.get(
    "/platform/collab-settings",
    response_model=CollabSettingsResponse,
    summary="Collab settings (`sak449-d`)",
    responses=with_long_tail_peel_503(),  # sak509-i
)
def get_collab_settings(request: Request, user: AuthUserDep) -> dict[str, Any]:
    _require_individual_collab_owner(request, user)
    return collab_settings_snapshot()


@router.put(
    "/platform/collab-settings",
    response_model=CollabSettingsResponse,
    summary="Update collab settings (`sak449-d`)",
    responses=with_long_tail_peel_503(),  # sak509-i
)
def put_collab_settings(
    body: CollabSettingsBody,
    request: Request,
    user: AuthUserDep,
) -> dict[str, Any]:
    _require_individual_collab_owner(request, user)
    set_runtime_collab_enabled(body.collab_enabled)
    save_persisted_collab_enabled(body.collab_enabled, repo_root=find_repo_root())
    return collab_settings_snapshot()


@router.post(
    "/platform/workspace-scaffold",
    response_model=WorkspaceScaffoldResponse,
    response_model_exclude_none=True,
    summary="Scaffold consumer tests (`sak480-d`)",
    responses={
        **platform_peel_json_openapi_responses(),  # sak496-f
        422: PROBLEM_RESPONSE_422,
    },
)
def post_workspace_scaffold(body: WorkspacePathBody, orch: OrchDep) -> dict[str, Any]:
    try:
        return scaffold_consumer_tests(Path(body.workspace_path.strip() or orch.repo_root))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.post(
    "/platform/workspace-precommit",
    response_model=WorkspaceScaffoldResponse,
    response_model_exclude_none=True,
    summary="Install workspace precommit (`sak480-d`)",
    responses=with_long_tail_peel_503({422: PROBLEM_RESPONSE_422}),  # sak510-g
)
def post_workspace_precommit(body: WorkspacePathBody, orch: OrchDep) -> dict[str, Any]:
    try:
        return install_workspace_precommit(Path(body.workspace_path.strip() or orch.repo_root))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


@router.get(
    "/platform/edition",
    response_model=PlatformEditionResponse,
    response_model_exclude_none=True,
    summary="Edition manifest (`sak449-d`)",
    responses=with_long_tail_peel_503(),  # sak509-h
)
def get_platform_edition() -> dict[str, Any]:
    body = edition_manifest()
    body["compose_profiles"] = enterprise_compose_profiles()
    return body


@router.get(
    "/platform/readiness",
    response_model=PlatformReadinessResponse,
    response_model_exclude_none=True,
    summary="Platform readiness (CAPACITY peel-aware; sak447-c/d / sak493-a)",
    responses=capacity_json_openapi_responses(),  # sak510-a
)
def get_platform_readiness(orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    try:
        return build_platform_readiness(repo_root=orch.repo_root, store=store)
    except Exception as exc:  # noqa: BLE001 — sak447-c
        from broker_client.flags import broker_capacity_enabled
        from hw.capacity_route import map_broker_capacity_http_miss

        if broker_capacity_enabled():
            return map_broker_capacity_http_miss(
                exc,
                feature="platform_readiness",
                miss_extra={"status": "degraded", "checks": {}},
            )
        raise


@router.get(
    "/platform/fleet-governance",
    response_model=FleetGovernanceResponse,
    response_model_exclude_none=True,
    summary="Fleet governance summary (`sak448-e`)",
    responses=with_long_tail_peel_503(),  # sak510-a
)
def get_platform_fleet_governance(
    archetype: str = "",
    tenant_slug: str = "",
) -> dict[str, Any]:
    from maker.fleet_governance_summary import fleet_governance_summary

    return fleet_governance_summary(
        archetype=archetype.strip() or None,
        tenant_slug=tenant_slug.strip() or None,
    )


@router.get(
    "/platform/workspace-readiness",
    response_model=WorkspaceReadinessResponse,
    response_model_exclude_none=True,
    summary="Workspace readiness (`sak448-e`; peel OpenAPI `sak494-g`)",
    responses=capacity_json_openapi_responses(),  # sak494-g
)
def get_workspace_readiness(
    workspace_path: str,
    orch: OrchDep,
) -> dict[str, Any]:
    return assess_workspace_readiness(Path(workspace_path.strip() or orch.repo_root))


@router.get(
    "/platform/playwright-bootstrap",
    response_model=PlaywrightBootstrapResponse,
    response_model_exclude_none=True,
    summary="Playwright bootstrap status (`sak449-d`)",
    responses=platform_bootstrap_json_openapi_responses(),  # sak495-c
)
def get_playwright_bootstrap() -> dict[str, Any]:
    return playwright_bootstrap_status()


@router.post(
    "/platform/playwright-bootstrap",
    response_model=PlaywrightBootstrapResponse,
    response_model_exclude_none=True,
    summary="Run Playwright bootstrap (`sak449-d`)",
    responses=platform_bootstrap_json_openapi_responses(),  # sak495-c
)
def post_playwright_bootstrap() -> dict[str, Any]:
    return run_playwright_bootstrap()


@router.get(
    "/platform/onboarding",
    response_model=PlatformOnboardingResponse,
    summary="Onboarding status (`sak447-d`)",
    responses=with_long_tail_peel_503(),  # sak510-b
)
def get_platform_onboarding() -> dict[str, Any]:
    return {"onboarded": is_onboarded_server()}


@router.post(
    "/platform/onboarding",
    response_model=PlatformOnboardingResponse,
    summary="Mark onboarded (`sak447-d`)",
    responses=with_long_tail_peel_503(),  # sak510-b
)
def post_platform_onboarding() -> dict[str, Any]:
    mark_onboarded_server()
    return {"onboarded": True}


@router.get(
    "/platform/optimizer-weights",
    response_model=PlatformOptimizerWeightsResponse,
    response_model_exclude_none=True,
    summary="Platform optimizer weights (`sak446-c`)",
    responses=with_long_tail_peel_503(),  # sak510-c
)
def get_optimizer_weights(
    user: AuthUserDep,
    weights_store: OptimizerWeightsStoreDep,
) -> dict[str, Any]:
    row = weights_store.get(user_id=user.user_id)
    return {"weights": row.weights, "updated_at": row.updated_at.isoformat()}


@router.put(
    "/platform/optimizer-weights",
    response_model=PlatformOptimizerWeightsResponse,
    response_model_exclude_none=True,
    summary="Update platform optimizer weights (`sak446-c`)",
    responses=with_long_tail_peel_503(),  # sak510-c
)
def put_optimizer_weights(
    body: OptimizerWeightsBody,
    user: AuthUserDep,
    weights_store: OptimizerWeightsStoreDep,
) -> dict[str, Any]:
    row = weights_store.put(user_id=user.user_id, weights=body.weights)
    return {"weights": row.weights, "updated_at": row.updated_at.isoformat()}


@router.get(
    "/platform/industry-critic-packs",
    response_model=IndustryCriticPacksResponse,
    response_model_exclude_none=True,
    summary="Industry critic packs (`sak480-d`)",
    responses=with_long_tail_peel_503(),  # sak510-g
)
def get_industry_critic_packs(orch: OrchDep) -> dict[str, Any]:
    return {
        "packs": list_industry_critic_packs(
            orch.repo_root,
            config_materializer=orch.config_materializer,
        ),
    }


@router.get(
    "/platform/safe-coding-preferences",
    response_model=SafeCodingPreferencesResponse,
    response_model_exclude_none=True,
    summary="Safe-coding preferences (`sak480-d`)",
    responses=with_long_tail_peel_503(),  # sak510-h
)
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


@router.put(
    "/platform/safe-coding-preferences",
    response_model=SafeCodingPreferencesResponse,
    response_model_exclude_none=True,
    summary="Update safe-coding preferences (`sak480-d`)",
    responses=with_long_tail_peel_503(),  # sak510-h
)
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
