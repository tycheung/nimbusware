from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep, OptionalUserDep
from nimbusware_api.user import maker_user_id_str
from nimbusware_maker.deploy_credential_vault import (
    load_deploy_credentials,
    save_deploy_credentials,
)
from nimbusware_maker.deploy_pipeline_events import (
    autopilot_may_auto_approve_deploy,
    deploy_approved_from_events,
    emit_deploy_apply_stages,
    emit_deploy_approved,
    emit_terraform_validate_stages,
)
from nimbusware_maker.terraform_validate import (
    apply_workspace_terraform,
    validate_workspace_terraform,
)

router = APIRouter(tags=["platform"])


class TerraformValidateBody(BaseModel):
    workspace_path: str = Field(min_length=1, max_length=2000)
    run_id: str | None = Field(default=None, max_length=36)


class DeployCredentialsBody(BaseModel):
    aws_profile: str | None = Field(default=None, max_length=200)
    github_repo: str | None = Field(default=None, max_length=200)
    workflow_path: str | None = Field(default=None, max_length=500)


class DeployApproveBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


class DeployApplyBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    workspace_path: str = Field(min_length=1, max_length=2000)


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


@router.post("/platform/deploy/apply")
def post_deploy_apply(
    body: DeployApplyBody,
    request: Request,
    orch: OrchDep,
    store: StoreDep,
    user: OptionalUserDep,
) -> dict[str, Any]:
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
    if not deploy_approved_from_events(rows):
        from nimbusware_orchestrator.autopilot_profiles import latest_autopilot_block_from_rows

        block = latest_autopilot_block_from_rows(rows)
        if not autopilot_may_auto_approve_deploy(block):
            raise HTTPException(
                status_code=403,
                detail=problem(
                    "deploy_approval_required",
                    "Record deploy approval before apply (or use deploy_hands_off autopilot profile)",
                ),
            )
        emit_deploy_approved(store, rid)
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    creds = load_deploy_credentials(uid, repo_root=orch.repo_root) if uid else {}
    if not creds.get("aws_profile") and not creds.get("github_repo"):
        result = {
            "status": "skipped",
            "detail": "No deploy credentials configured — plan-only lane",
        }
        emit_deploy_apply_stages(store, rid, result)
        return result
    ws = Path(body.workspace_path.strip())
    if not ws.is_absolute():
        ws = (orch.repo_root / ws).resolve()
    try:
        result = apply_workspace_terraform(ws)
    except OSError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    emit_deploy_apply_stages(store, rid, result)
    return result


@router.post("/platform/deploy/terraform-validate")
def post_terraform_validate(
    body: TerraformValidateBody,
    orch: OrchDep,
    store: StoreDep,
) -> dict[str, Any]:
    ws = Path(body.workspace_path.strip())
    if not ws.is_absolute():
        ws = (orch.repo_root / ws).resolve()
    try:
        result = validate_workspace_terraform(ws)
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


@router.put("/platform/deploy/credentials")
def put_deploy_credentials(
    body: DeployCredentialsBody,
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
    try:
        return save_deploy_credentials(
            uid,
            aws_profile=body.aws_profile,
            github_repo=body.github_repo,
            workflow_path=body.workflow_path,
            repo_root=orch.repo_root,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


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
