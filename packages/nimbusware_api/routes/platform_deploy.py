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
from nimbusware_env.env_flags import env_str
from nimbusware_iam.context import get_auth_context
from nimbusware_maker.deploy_approval_enforcement import (
    resolve_deploy_approver_context,
    user_may_record_deploy_approval,
)
from nimbusware_maker.deploy_credential_vault import (
    list_deploy_audit_events,
    load_deploy_credentials,
)
from nimbusware_maker.deploy_pipeline_events import (
    deploy_apply_ready,
    emit_deploy_approved,
    emit_terraform_validate_stages,
    manifest_from_events,
)
from nimbusware_maker.deploy_target_enforcement import (
    deploy_environment_catalog,
    resolve_deploy_environment,
    validate_credential_scopes,
    validate_manifest_deploy_target,
)
from nimbusware_maker.terraform_validate import RollbackMode, validate_workspace_terraform

router = APIRouter(tags=["platform"])


class TerraformValidateBody(BaseModel):
    workspace_path: str = Field(min_length=1, max_length=2000)
    run_id: str | None = Field(default=None, max_length=36)
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeployCredentialsBody(BaseModel):
    aws_profile: str | None = Field(default=None, max_length=200)
    github_repo: str | None = Field(default=None, max_length=200)
    workflow_path: str | None = Field(default=None, max_length=500)
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeployApproveBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


class DeployApplyBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    workspace_path: str = Field(min_length=1, max_length=2000)
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeploySmokeBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    api_url: str | None = Field(default=None, max_length=2000)
    web_url: str | None = Field(default=None, max_length=2000)
    use_playwright: bool = False


class DeployRollbackBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    workspace_path: str = Field(min_length=1, max_length=2000)
    mode: RollbackMode = "destroy"
    deploy_environment: str | None = Field(default=None, max_length=32)


class DeployCiPollBody(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)
    branch: str | None = Field(default=None, max_length=200)


def resolved_deploy_environment(
    *,
    explicit: str | None,
    creds: dict[str, Any],
    rows: list[dict[str, Any]],
) -> str:
    try:
        return resolve_deploy_environment(
            explicit=explicit,
            credentials=creds,
            manifest_raw=manifest_from_events(rows),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc


def deploy_policy_context() -> tuple[str | None, str]:
    ctx = get_auth_context()
    tenant_slug = ctx.tenant_slug if ctx is not None else None
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    return tenant_slug, setup_bundle


def deploy_approval_chain_for_tenant(tenant_slug: str | None, setup_bundle: str) -> str:
    if setup_bundle != "enterprise":
        return "maker_only"
    from nimbusware_orchestrator.fleet_deploy_approval_policy import tenant_deploy_approval_policy

    return tenant_deploy_approval_policy(tenant_slug).deploy_approval_chain


def enforce_manifest_deploy_target(
    rows: list[dict[str, Any]],
    *,
    tenant_slug: str | None,
    setup_bundle: str,
) -> None:
    ok, detail = validate_manifest_deploy_target(
        manifest_from_events(rows),
        tenant_slug=tenant_slug,
        setup_bundle=setup_bundle,
    )
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=problem("deploy_target_denied", detail or "deploy target not allowed"),
        )


def enforce_credential_scopes(
    creds: dict[str, Any],
    *,
    tenant_slug: str | None,
    setup_bundle: str,
) -> None:
    ok, detail = validate_credential_scopes(
        creds,
        tenant_slug=tenant_slug,
        setup_bundle=setup_bundle,
    )
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=problem("deploy_credential_scope_denied", detail or "credential scope denied"),
        )


from nimbusware_api.routes.platform_deploy_mutations import router as mutations_router

router.include_router(mutations_router)


@router.get("/platform/deploy/environments")
def get_deploy_environments() -> dict[str, Any]:
    return deploy_environment_catalog()


@router.post("/platform/deploy/approve")
def post_deploy_approve(
    body: DeployApproveBody,
    request: Request,
    store: StoreDep,
    user: OptionalUserDep,
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
    tenant_slug, setup_bundle = deploy_policy_context()
    chain = deploy_approval_chain_for_tenant(tenant_slug, setup_bundle)
    ctx = get_auth_context()
    scopes = ctx.api_scopes if ctx is not None else ()
    uid, is_admin, _ = resolve_deploy_approver_context(user, api_scopes=scopes)
    if not uid:
        uid = maker_user_id_str(request) or None
    ok, detail, kind = user_may_record_deploy_approval(
        user_id=uid,
        is_fleet_admin=is_admin,
        session_role=None,
        chain=chain,
        rows=rows,
    )
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=problem("deploy_approval_denied", detail or "not authorized to approve deploy"),
        )
    emit_deploy_approved(store, rid, approver_user_id=uid, approval_kind=kind)
    status = "approved"
    if chain == "dual_control" and not deploy_apply_ready(
        store.list_run_events(str(rid)),
        deploy_approval_chain=chain,
    ):
        status = "partial"
    return {"run_id": str(rid), "status": status, "approval_kind": kind}


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


@router.get("/platform/deploy/audit")
def get_deploy_audit(
    orch: OrchDep,
    user: AuthUserDep,
    run_id: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "user identity required"),
        )
    rid = run_id.strip()
    if rid:
        try:
            UUID(rid)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=problem("invalid_request", "run_id must be a UUID"),
            ) from exc
    events = list_deploy_audit_events(
        run_id=rid,
        limit=limit,
        repo_root=orch.repo_root,
    )
    return {"events": events, "run_id": rid or None, "count": len(events)}


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
