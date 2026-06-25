from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.deps import OptimizerWeightsStoreDep, OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.platform_hardware import router as hardware_router
from nimbusware_api.routes.platform_model_routing import router as model_routing_router
from nimbusware_api.routes.platform_operator_profiles import router as operator_profiles_router
from nimbusware_api.routes.platform_user_profiles import router as user_profiles_router
from nimbusware_env.edition import edition_manifest, enterprise_compose_profiles
from nimbusware_maker.consumer_precommit_install import install_workspace_precommit
from nimbusware_maker.consumer_test_scaffold import scaffold_consumer_tests
from nimbusware_maker.onboarding import is_onboarded_server, mark_onboarded_server
from nimbusware_maker.readiness import build_platform_readiness
from nimbusware_maker.workspace_readiness import assess_workspace_readiness

router = APIRouter(tags=["platform"])
router.include_router(hardware_router)
router.include_router(user_profiles_router)
router.include_router(operator_profiles_router)
router.include_router(model_routing_router)


class OptimizerWeightsBody(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)


class WorkspacePathBody(BaseModel):
    workspace_path: str = Field(min_length=1, max_length=2000)


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


@router.get("/platform/workspace-readiness")
def get_workspace_readiness(
    workspace_path: str,
    orch: OrchDep,
) -> dict[str, Any]:
    return assess_workspace_readiness(Path(workspace_path.strip() or orch.repo_root))


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
