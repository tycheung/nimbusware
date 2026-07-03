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
    FleetSlicePolicy,
    FleetStackPolicy,
    load_fleet_slice_policies,
    load_fleet_stack_policies,
    normalize_allowed_stacks,
    save_fleet_slice_policies,
    save_fleet_stack_policies,
    tenant_slice_policy,
    tenant_stack_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetSlicePolicyBody(BaseModel):
    slice_budget_preset: str = Field(default="standard", max_length=32)
    max_files: int = Field(ge=1, le=20, default=3)
    max_loc: int = Field(ge=1, le=500, default=120)
    require_unanimous_gate: bool = True


class FleetStackPolicyBody(BaseModel):
    allowed_stacks: dict[str, str] = Field(default_factory=dict)


@router.get("/tenants/{tenant_ref}/slice-policy")
def get_fleet_slice_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return tenant_slice_policy(slug).to_dict()


@router.put("/tenants/{tenant_ref}/slice-policy")
def put_fleet_slice_policy(
    tenant_ref: str,
    body: FleetSlicePolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policies = load_fleet_slice_policies()
    policies[slug] = FleetSlicePolicy(
        tenant_slug=slug,
        slice_budget_preset=body.slice_budget_preset.strip(),
        max_files=body.max_files,
        max_loc=body.max_loc,
        require_unanimous_gate=body.require_unanimous_gate,
    )
    save_fleet_slice_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="slice")
    saved: FleetSlicePolicy = policies[slug]
    return dict(saved.to_dict())


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
    allowed = normalize_allowed_stacks(body.allowed_stacks)
    policies = load_fleet_stack_policies()
    policies[slug] = FleetStackPolicy(tenant_slug=slug, allowed_stacks=allowed)
    save_fleet_stack_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="stack")
    saved: FleetStackPolicy = policies[slug]
    return dict(saved.to_dict())
