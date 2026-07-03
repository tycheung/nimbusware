from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from api.deps import OrchDep, StoreDep
from api.errors import problem
from api.routes.auth import AuthUserDep, OptionalUserDep
from api.routes.platform_deploy import (
    DeployApplyBody,
    DeployCiPollBody,
    DeployCredentialsBody,
    DeployRollbackBody,
    DeploySmokeBody,
    deploy_approval_chain_for_tenant,
    deploy_policy_context,
    enforce_credential_scopes,
    enforce_manifest_deploy_target,
    resolved_deploy_environment,
)
from api.user import maker_user_id_str
from maker.deploy.credential_vault import (
    audit_credentials_updated,
    audit_credentials_used,
    load_deploy_credentials,
    save_deploy_credentials,
)
from maker.deploy.pipeline_events import (
    autopilot_may_auto_approve_deploy,
    deploy_apply_passed_from_events,
    deploy_apply_ready,
    deploy_approved_from_events,
    deploy_rollback_passed_from_events,
    emit_ci_workflow_stages,
    emit_deploy_apply_stages,
    emit_deploy_approved,
    emit_deploy_rollback_stages,
    emit_deploy_smoke_stages,
    live_urls_from_events,
    manifest_from_events,
)
from maker.deploy.smoke import run_deploy_smoke
from maker.deploy.target_enforcement import (
    credential_scope_labels,
    deploy_target_from_credentials,
    deploy_target_from_manifest,
)
from maker.github_workflow_poll import poll_github_workflow_run
from maker.terraform_validate import (
    apply_workspace_terraform,
    rollback_workspace_terraform,
)
from orchestrator.git_outputs import run_branch_name

router = APIRouter(tags=["platform"])


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
    tenant_slug, setup_bundle = deploy_policy_context()
    approval_chain = deploy_approval_chain_for_tenant(tenant_slug, setup_bundle)
    if not deploy_apply_ready(rows, deploy_approval_chain=approval_chain):
        from orchestrator.profiles.autopilot_profiles import latest_autopilot_block_from_rows

        block = latest_autopilot_block_from_rows(rows)
        if not autopilot_may_auto_approve_deploy(block):
            code = (
                "deploy_dual_control_pending"
                if approval_chain == "dual_control"
                else "deploy_approval_required"
            )
            msg = (
                "Fleet admin dual-control approval required before apply"
                if approval_chain == "dual_control"
                else "Record deploy approval before apply (or use deploy_hands_off autopilot profile)"
            )
            raise HTTPException(
                status_code=403,
                detail=problem(code, msg),
            )
        emit_deploy_approved(store, rid, approval_kind="autopilot")
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    tenant_slug, setup_bundle = deploy_policy_context()
    enforce_manifest_deploy_target(rows, tenant_slug=tenant_slug, setup_bundle=setup_bundle)
    creds = load_deploy_credentials(uid, repo_root=orch.repo_root) if uid else {}
    enforce_credential_scopes(creds, tenant_slug=tenant_slug, setup_bundle=setup_bundle)
    deploy_env = resolved_deploy_environment(
        explicit=body.deploy_environment,
        creds=creds,
        rows=rows,
    )
    if not creds.get("aws_profile") and not creds.get("github_repo"):
        result = {
            "status": "skipped",
            "detail": "No deploy credentials configured — plan-only lane",
            "deploy_environment": deploy_env,
        }
        emit_deploy_apply_stages(store, rid, result)
        return result
    audit_credentials_used(
        user_id=uid,
        run_id=str(rid),
        action="apply",
        tenant_slug=tenant_slug,
        deploy_target=deploy_target_from_manifest(manifest_from_events(rows))
        or deploy_target_from_credentials(creds),
        scopes=credential_scope_labels(creds),
        repo_root=orch.repo_root,
    )
    ws = Path(body.workspace_path.strip())
    if not ws.is_absolute():
        ws = (orch.repo_root / ws).resolve()
    try:
        result = apply_workspace_terraform(ws, deploy_environment=deploy_env)
    except OSError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    emit_deploy_apply_stages(store, rid, result)
    if result.get("status") == "passed" and (result.get("api_url") or result.get("web_url")):
        smoke = run_deploy_smoke(
            api_url=str(result["api_url"]) if result.get("api_url") else None,
            web_url=str(result["web_url"]) if result.get("web_url") else None,
        )
        emit_deploy_smoke_stages(store, rid, smoke)
        result["smoke"] = smoke
    return result


@router.post("/platform/deploy/smoke")
def post_deploy_smoke(
    body: DeploySmokeBody,
    store: StoreDep,
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
    if not deploy_apply_passed_from_events(rows):
        raise HTTPException(
            status_code=403,
            detail=problem(
                "deploy_apply_required",
                "Record a successful deploy apply before smoke tests",
            ),
        )
    urls = live_urls_from_events(rows)
    api_url = (body.api_url or urls.get("api_url") or "").strip() or None
    web_url = (body.web_url or urls.get("web_url") or "").strip() or None
    result = run_deploy_smoke(
        api_url=api_url,
        web_url=web_url,
        use_playwright=body.use_playwright,
    )
    emit_deploy_smoke_stages(store, rid, result)
    return result


@router.post("/platform/deploy/rollback")
def post_deploy_rollback(
    body: DeployRollbackBody,
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
    if not deploy_apply_passed_from_events(rows):
        raise HTTPException(
            status_code=403,
            detail=problem(
                "deploy_apply_required",
                "Record a successful deploy apply before rollback",
            ),
        )
    if deploy_rollback_passed_from_events(rows):
        raise HTTPException(
            status_code=403,
            detail=problem(
                "deploy_rollback_already_recorded", "Rollback already completed for this run"
            ),
        )
    if not deploy_approved_from_events(rows):
        raise HTTPException(
            status_code=403,
            detail=problem("deploy_approval_required", "Record deploy approval before rollback"),
        )
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    tenant_slug, setup_bundle = deploy_policy_context()
    creds = load_deploy_credentials(uid, repo_root=orch.repo_root) if uid else {}
    enforce_credential_scopes(creds, tenant_slug=tenant_slug, setup_bundle=setup_bundle)
    deploy_env = resolved_deploy_environment(
        explicit=body.deploy_environment,
        creds=creds,
        rows=rows,
    )
    if not creds.get("aws_profile") and not creds.get("github_repo"):
        result = {
            "status": "skipped",
            "detail": "No deploy credentials configured — plan-only lane",
            "rollback_mode": body.mode,
            "deploy_environment": deploy_env,
        }
        emit_deploy_rollback_stages(store, rid, result)
        return result
    audit_credentials_used(
        user_id=uid,
        run_id=str(rid),
        action="rollback",
        tenant_slug=tenant_slug,
        deploy_target=deploy_target_from_manifest(manifest_from_events(rows))
        or deploy_target_from_credentials(creds),
        scopes=credential_scope_labels(creds),
        repo_root=orch.repo_root,
    )
    ws = Path(body.workspace_path.strip())
    if not ws.is_absolute():
        ws = (orch.repo_root / ws).resolve()
    try:
        result = rollback_workspace_terraform(ws, mode=body.mode, deploy_environment=deploy_env)
    except OSError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    emit_deploy_rollback_stages(store, rid, result)
    return result


@router.post("/platform/deploy/ci-poll")
def post_deploy_ci_poll(
    body: DeployCiPollBody,
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
    uid = str(user.user_id) if user is not None else maker_user_id_str(request)
    creds = load_deploy_credentials(uid, repo_root=orch.repo_root) if uid else {}
    github_repo = str(creds.get("github_repo") or "").strip()
    if not github_repo:
        return {"status": "skipped", "detail": "No GitHub repo configured for workflow polling"}
    branch = (body.branch or run_branch_name(rid)).strip()
    result = poll_github_workflow_run(
        github_repo=github_repo,
        workflow_path=str(creds.get("workflow_path") or "").strip(),
        branch=branch,
    )
    if result.get("status") in {"passed", "failed", "running"}:
        emit_ci_workflow_stages(store, rid, result)
    return result


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
        tenant_slug, setup_bundle = deploy_policy_context()
        candidate = {
            "aws_profile": str(body.aws_profile or "").strip(),
            "github_repo": str(body.github_repo or "").strip(),
        }
        enforce_credential_scopes(
            candidate,
            tenant_slug=tenant_slug,
            setup_bundle=setup_bundle,
        )
        saved = save_deploy_credentials(
            uid,
            aws_profile=body.aws_profile,
            github_repo=body.github_repo,
            workflow_path=body.workflow_path,
            deploy_environment=body.deploy_environment,
            repo_root=orch.repo_root,
        )
        audit_credentials_updated(
            user_id=uid,
            tenant_slug=tenant_slug,
            scopes=credential_scope_labels(saved),
            deploy_target=deploy_target_from_credentials(saved),
            repo_root=orch.repo_root,
        )
        return saved
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
