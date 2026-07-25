from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.routes.enterprise._fleet_policy_helpers import (
    fleet_tenant_policy_get,
    fleet_tenant_policy_put,
    tenant_slug_for_ref,
)
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import with_enterprise_peel_503
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


class FleetSlicePolicyResponse(BaseModel):
    """GET/PUT tenant slice-policy (`sak482-g`)."""

    model_config = {"extra": "allow"}

    tenant_slug: str | None = None
    slice_budget_preset: str | None = None
    max_files: int | None = None
    max_loc: int | None = None
    require_unanimous_gate: bool | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class FleetStackPolicyResponse(BaseModel):
    """GET/PUT tenant stack-policy (`sak482-g`)."""

    model_config = {"extra": "allow"}

    tenant_slug: str | None = None
    allowed_stacks: dict[str, str] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/tenants/{tenant_ref}/slice-policy",
    response_model=FleetSlicePolicyResponse,
    response_model_exclude_none=True,
    summary="Fleet slice policy GET (`sak482-g`)",
    responses=with_enterprise_peel_503(),  # sak518-i
)
def get_fleet_slice_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    return fleet_tenant_policy_get(iam, tenant_ref, tenant_slice_policy)


@router.put(
    "/tenants/{tenant_ref}/slice-policy",
    response_model=FleetSlicePolicyResponse,
    response_model_exclude_none=True,
    summary="Fleet slice policy PUT (`sak482-g`)",
    responses=with_enterprise_peel_503(),  # sak518-i
)
def put_fleet_slice_policy(
    tenant_ref: str,
    body: FleetSlicePolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    policy = FleetSlicePolicy(
        tenant_slug=slug,
        slice_budget_preset=body.slice_budget_preset.strip(),
        max_files=body.max_files,
        max_loc=body.max_loc,
        require_unanimous_gate=body.require_unanimous_gate,
    )
    return fleet_tenant_policy_put(
        iam,
        tenant_ref,
        policy_kind="slice",
        policy=policy,
        load_policies=load_fleet_slice_policies,
        save_policies=save_fleet_slice_policies,
    )


@router.get(
    "/tenants/{tenant_ref}/stack-policy",
    response_model=FleetStackPolicyResponse,
    response_model_exclude_none=True,
    summary="Fleet stack policy GET (`sak482-g`)",
    responses=with_enterprise_peel_503(),  # sak519-a
)
def get_fleet_stack_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    return fleet_tenant_policy_get(iam, tenant_ref, tenant_stack_policy)


@router.put(
    "/tenants/{tenant_ref}/stack-policy",
    response_model=FleetStackPolicyResponse,
    response_model_exclude_none=True,
    summary="Fleet stack policy PUT (`sak482-g`)",
    responses=with_enterprise_peel_503(),  # sak519-a
)
def put_fleet_stack_policy(
    tenant_ref: str,
    body: FleetStackPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)
    allowed = normalize_allowed_stacks(body.allowed_stacks)
    policy = FleetStackPolicy(tenant_slug=slug, allowed_stacks=allowed)
    return fleet_tenant_policy_put(
        iam,
        tenant_ref,
        policy_kind="stack",
        policy=policy,
        load_policies=load_fleet_stack_policies,
        save_policies=save_fleet_stack_policies,
    )
