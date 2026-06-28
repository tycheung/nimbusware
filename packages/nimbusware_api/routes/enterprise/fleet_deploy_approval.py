from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from nimbusware_api.routes.enterprise.iam_audit import log_fleet_policy_updated
from nimbusware_orchestrator.fleet_deploy_approval_policy import (
    VALID_DEPLOY_APPROVAL_CHAINS,
    FleetDeployApprovalPolicy,
    load_fleet_deploy_approval_policies,
    save_fleet_deploy_approval_policies,
    tenant_deploy_approval_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetDeployApprovalPolicyBody(BaseModel):
    deploy_approval_chain: str = Field(default="maker_only", max_length=32)


@router.get("/tenants/{tenant_ref}/deploy-approval-policy")
def get_fleet_deploy_approval_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return tenant_deploy_approval_policy(slug).to_dict()


@router.put("/tenants/{tenant_ref}/deploy-approval-policy")
def put_fleet_deploy_approval_policy(
    tenant_ref: str,
    body: FleetDeployApprovalPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
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
    return policies[slug].to_dict()
