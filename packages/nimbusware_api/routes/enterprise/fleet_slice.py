from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from nimbusware_api.routes.enterprise.iam_audit import log_fleet_policy_updated
from nimbusware_orchestrator.fleet_slice_policy import (
    FleetSlicePolicy,
    load_fleet_slice_policies,
    save_fleet_slice_policies,
    tenant_slice_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetSlicePolicyBody(BaseModel):
    slice_budget_preset: str = Field(default="standard", max_length=32)
    max_files: int = Field(ge=1, le=20, default=3)
    max_loc: int = Field(ge=1, le=500, default=120)
    require_unanimous_gate: bool = True


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
    return saved.to_dict()
