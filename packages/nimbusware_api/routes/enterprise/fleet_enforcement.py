from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_orchestrator.fleet_enforcement_policy import (
    FleetEnforcementPolicy,
    load_fleet_enforcement_policies,
    save_fleet_enforcement_policies,
    tenant_enforcement_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetEnforcementPolicyBody(BaseModel):
    min_enforcement_level: int = Field(ge=0, le=10, default=0)
    max_enforcement_level: int = Field(ge=0, le=10, default=10)

    @model_validator(mode="after")
    def _min_lte_max(self) -> FleetEnforcementPolicyBody:
        if self.min_enforcement_level > self.max_enforcement_level:
            raise ValueError("min_enforcement_level must be <= max_enforcement_level")
        return self


def _tenant_slug_for_ref(iam: IamStoreDep, tenant_ref: str) -> str:
    ref = tenant_ref.strip()
    if not ref:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_tenant", "tenant reference required"),
        )
    try:
        tid = UUID(ref)
        tenant = iam.get_tenant(tid)
        if tenant is None:
            raise HTTPException(
                status_code=404,
                detail=problem("tenant_not_found", f"unknown tenant_id: {ref}"),
            )
        return tenant.slug
    except ValueError:
        for tenant in iam.list_tenants():
            if tenant.slug == ref:
                return tenant.slug
        return ref


@router.get("/tenants/{tenant_ref}/enforcement-policy")
def get_tenant_enforcement_policy(
    tenant_ref: str,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policy = tenant_enforcement_policy(slug)
    return policy.to_dict()


@router.put("/tenants/{tenant_ref}/enforcement-policy")
def put_tenant_enforcement_policy(
    tenant_ref: str,
    body: FleetEnforcementPolicyBody,
    _admin: AdminDep,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policy = FleetEnforcementPolicy(
        tenant_slug=slug,
        min_enforcement_level=body.min_enforcement_level,
        max_enforcement_level=body.max_enforcement_level,
    )
    policies = load_fleet_enforcement_policies()
    policies[slug] = policy
    save_fleet_enforcement_policies(policies)
    return policy.to_dict()
