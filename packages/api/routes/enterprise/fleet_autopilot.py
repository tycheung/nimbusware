from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.admin import AdminDep
from api.deps import IamStoreDep
from api.errors import problem
from api.routes.enterprise.core import EnterpriseDep
from api.routes.enterprise.iam_audit import log_fleet_policy_updated
from orchestrator.autopilot_profiles import CHECKPOINT_CATALOG
from orchestrator.fleet_policies import (
    FleetAutopilotPolicy,
    load_fleet_autopilot_policies,
    save_fleet_autopilot_policies,
    tenant_autopilot_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetAutopilotPolicyBody(BaseModel):
    max_autopilot_level: int = Field(ge=0, le=10, default=10)
    required_checkpoints: list[str] = Field(default_factory=list)


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


@router.get("/tenants/{tenant_ref}/autopilot-policy")
def get_tenant_autopilot_policy(
    tenant_ref: str,
    _gate: EnterpriseDep,
    iam: IamStoreDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    policy = tenant_autopilot_policy(slug)
    return policy.to_dict()


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
    policies = load_fleet_autopilot_policies()
    policies[slug] = policy
    save_fleet_autopilot_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="autopilot")
    return policy.to_dict()
