from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep
from nimbusware_api.routes.platform_deploy_models import (
    DeployApproveBody,
    TerraformValidateBody,
)
from nimbusware_api.routes.platform_deploy_mutations import router as mutations_router
from nimbusware_api.routes.platform_deploy_support import resolved_deploy_environment
from nimbusware_api.user import maker_user_id_str
from nimbusware_maker.deploy_credential_vault import load_deploy_credentials
from nimbusware_maker.deploy_environments import deploy_environment_catalog
from nimbusware_maker.deploy_pipeline_events import (
    emit_deploy_approved,
    emit_terraform_validate_stages,
)
from nimbusware_maker.terraform_validate import validate_workspace_terraform

router = APIRouter(tags=["platform"])
router.include_router(mutations_router)


@router.get("/platform/deploy/environments")
def get_deploy_environments() -> dict[str, Any]:
    return deploy_environment_catalog()


@router.post("/platform/deploy/approve")
def post_deploy_approve(
    body: DeployApproveBody,
    store: StoreDep,
) -> dict[str, str]:
    try:
        rid = UUID(body.run_id.strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "run_id must be a UUID"),
        ) from exc
    rows = store.list_run_events(str(rid))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(rid)}),
        )
    emit_deploy_approved(store, rid)
    return {"run_id": str(rid), "status": "approved"}


@router.post("/platform/deploy/terraform-validate")
def post_terraform_validate(
    body: TerraformValidateBody,
    orch: OrchDep,
    store: StoreDep,
) -> dict[str, Any]:
    ws = Path(body.workspace_path.strip())
    if not ws.is_absolute():
        ws = (orch.repo_root / ws).resolve()
    deploy_env = body.deploy_environment
    if body.run_id and not deploy_env:
        try:
            rid = UUID(body.run_id.strip())
            rows = store.list_run_events(str(rid))
            deploy_env = resolved_deploy_environment(explicit=None, creds={}, rows=rows)
        except ValueError:
            pass
    try:
        result = validate_workspace_terraform(ws, deploy_environment=deploy_env)
    except OSError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    if body.run_id:
        try:
            rid = UUID(body.run_id.strip())
            rows = store.list_run_events(str(rid))
            if rows:
                emit_terraform_validate_stages(store, rid, result)
        except ValueError:
            pass
    return result


@router.get("/platform/deploy/credentials")
def get_deploy_credentials(
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
    return load_deploy_credentials(uid, repo_root=orch.repo_root)


@router.get("/platform/deploy/github-workflow-template")
def get_github_workflow_template(orch: OrchDep) -> dict[str, Any]:
    path = orch.repo_root / "configs" / "deploy" / "github_actions_nimbusware.yaml"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "workflow template missing"),
        )
    return {
        "path": ".github/workflows/nimbusware-deploy.yml",
        "content": path.read_text(encoding="utf-8"),
    }