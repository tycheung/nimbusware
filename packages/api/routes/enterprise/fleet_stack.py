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
    FleetStackPolicy,
    load_fleet_stack_policies,
    save_fleet_stack_policies,
    tenant_stack_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetStackPolicyBody(BaseModel):
    allowed_stacks: dict[str, str] = Field(default_factory=dict)


@router.get("/tenants/{tenant_ref}/stack-policy")
def get_fleet_stack_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return tenant_stack_policy(slug).to_dict()


@router.put("/tenants/{tenant_ref}/stack-policy")
def put_fleet_stack_policy(
    tenant_ref: str,
    body: FleetStackPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    from orchestrator.fleet.policies import normalize_allowed_stacks

    allowed = normalize_allowed_stacks(body.allowed_stacks)
    policies = load_fleet_stack_policies()
    policies[slug] = FleetStackPolicy(tenant_slug=slug, allowed_stacks=allowed)
    save_fleet_stack_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="stack")
    saved: FleetStackPolicy = policies[slug]
    return saved.to_dict()
