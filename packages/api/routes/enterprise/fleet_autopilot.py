from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.routes.enterprise._fleet_policy_helpers import (
    fleet_tenant_policy_get,
    fleet_tenant_policy_put,
)
from api.routes.enterprise.core import EnterpriseDep
from api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from orchestrator.fleet.policies import (
    FleetAutopilotPolicy,
    load_fleet_autopilot_policies,
    save_fleet_autopilot_policies,
    tenant_autopilot_policy,
)
from orchestrator.profiles.autopilot_profiles import CHECKPOINT_CATALOG

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetAutopilotPolicyBody(BaseModel):
    max_autopilot_level: int = Field(ge=0, le=10, default=10)
    required_checkpoints: list[str] = Field(default_factory=list)


@router.get("/tenants/{tenant_ref}/autopilot-policy")
def get_tenant_autopilot_policy(
    tenant_ref: str,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    return fleet_tenant_policy_get(iam, tenant_ref, tenant_autopilot_policy)


@router.put("/tenants/{tenant_ref}/autopilot-policy")
def put_tenant_autopilot_policy(
    tenant_ref: str,
    body: FleetAutopilotPolicyBody,
    _admin: AdminDep,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    checkpoints = {c for c in body.required_checkpoints if c in CHECKPOINT_CATALOG}
    policy = FleetAutopilotPolicy(
        tenant_slug=slug,
        max_autopilot_level=body.max_autopilot_level,
        required_checkpoints=frozenset(checkpoints),
    )
    return fleet_tenant_policy_put(
        iam,
        tenant_ref,
        policy_kind="autopilot",
        policy=policy,
        load_policies=load_fleet_autopilot_policies,
        save_policies=save_fleet_autopilot_policies,
    )
