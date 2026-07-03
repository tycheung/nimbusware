from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.routes.enterprise.core import EnterpriseDep
from api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from api.routes.enterprise.iam_audit import log_fleet_policy_updated
from orchestrator.fleet.policies import (
    FleetDeployPolicy,
    load_fleet_deploy_policies,
    save_fleet_deploy_policies,
    tenant_deploy_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetDeployPolicyBody(BaseModel):
    allowed_deploy_targets: list[str] = Field(default_factory=list, max_length=20)


@router.get("/tenants/{tenant_ref}/deploy-policy")
def get_fleet_deploy_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return tenant_deploy_policy(slug).to_dict()


@router.put("/tenants/{tenant_ref}/deploy-policy")
def put_fleet_deploy_policy(
    tenant_ref: str,
    body: FleetDeployPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    targets = tuple(str(t).strip() for t in body.allowed_deploy_targets if str(t).strip())
    policies = load_fleet_deploy_policies()
    policies[slug] = FleetDeployPolicy(
        tenant_slug=slug,
        allowed_deploy_targets=targets,
    )
    save_fleet_deploy_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="deploy")
    saved: FleetDeployPolicy = policies[slug]
    return saved.to_dict()
