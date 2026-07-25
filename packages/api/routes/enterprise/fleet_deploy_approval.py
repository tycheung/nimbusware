from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.routes.enterprise._fleet_policy_helpers import tenant_slug_for_ref
from api.routes.enterprise.core import EnterpriseDep
from api.routes.enterprise.iam_audit import log_fleet_policy_updated
from api.schemas.peel_responses import with_enterprise_peel_503
from orchestrator.fleet.policies import (
    VALID_DEPLOY_APPROVAL_CHAINS,
    FleetDeployApprovalPolicy,
    load_fleet_deploy_approval_policies,
    save_fleet_deploy_approval_policies,
    tenant_deploy_approval_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetDeployApprovalPolicyBody(BaseModel):
    deploy_approval_chain: str = Field(default="maker_only", max_length=32)


class FleetDeployApprovalPolicyResponse(BaseModel):
    """GET/PUT tenant deploy-approval-policy (`sak483-f`)."""

    model_config = {"extra": "allow"}

    tenant_slug: str | None = None
    deploy_approval_chain: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/tenants/{tenant_ref}/deploy-approval-policy",
    response_model=FleetDeployApprovalPolicyResponse,
    response_model_exclude_none=True,
    summary="Tenant deploy approval policy GET (`sak483-f`)",
    responses=with_enterprise_peel_503(),  # sak504-c
)
def get_fleet_deploy_approval_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    return tenant_deploy_approval_policy(slug).to_dict()


@router.put(
    "/tenants/{tenant_ref}/deploy-approval-policy",
    response_model=FleetDeployApprovalPolicyResponse,
    response_model_exclude_none=True,
    summary="Tenant deploy approval policy PUT (`sak483-f`)",
    responses=with_enterprise_peel_503(),  # sak504-c
)
def put_fleet_deploy_approval_policy(
    tenant_ref: str,
    body: FleetDeployApprovalPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    chain = str(body.deploy_approval_chain or "maker_only").strip()
    if chain not in VALID_DEPLOY_APPROVAL_CHAINS:
        chain = "maker_only"
    policies = load_fleet_deploy_approval_policies()
    policies[slug] = FleetDeployApprovalPolicy(
        tenant_slug=slug,
        deploy_approval_chain=chain,  # type: ignore[arg-type]
    )
    save_fleet_deploy_approval_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="deploy_approval")
    saved: FleetDeployApprovalPolicy = policies[slug]
    return saved.to_dict()
