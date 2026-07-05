from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.routes.enterprise._fleet_policy_helpers import (
    fleet_tenant_policy_get,
    fleet_tenant_policy_put,
    tenant_slug_for_ref,
)
from api.routes.enterprise.core import EnterpriseDep
from orchestrator.fleet.policies import (
    FleetEnforcementPolicy,
    load_fleet_enforcement_policies,
    save_fleet_enforcement_policies,
    tenant_enforcement_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetEnforcementPolicyBody(BaseModel):
    min_enforcement_level: int = Field(ge=0, le=10, default=0)
    max_enforcement_level: int = Field(ge=0, le=10, default=10)
    required_enforcement_profile_id: str = Field(default="", max_length=120)

    @model_validator(mode="after")
    def _min_lte_max(self) -> FleetEnforcementPolicyBody:
        if self.min_enforcement_level > self.max_enforcement_level:
            raise ValueError("min_enforcement_level must be <= max_enforcement_level")
        return self


@router.get("/tenants/{tenant_ref}/enforcement-policy")
def get_tenant_enforcement_policy(
    tenant_ref: str,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    return fleet_tenant_policy_get(iam, tenant_ref, tenant_enforcement_policy)


@router.put("/tenants/{tenant_ref}/enforcement-policy")
def put_tenant_enforcement_policy(
    tenant_ref: str,
    body: FleetEnforcementPolicyBody,
    _admin: AdminDep,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = tenant_slug_for_ref(iam, tenant_ref)

    def _save(policies: dict[str, Any]) -> None:
        save_fleet_enforcement_policies(policies)

    return fleet_tenant_policy_put(
        iam,
        tenant_ref,
        policy_kind="enforcement",
        policy=FleetEnforcementPolicy(
            tenant_slug=slug,
            min_enforcement_level=body.min_enforcement_level,
            max_enforcement_level=body.max_enforcement_level,
            required_enforcement_profile_id=body.required_enforcement_profile_id.strip(),
        ),
        load_policies=load_fleet_enforcement_policies,
        save_policies=_save,
    )
