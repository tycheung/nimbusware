from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.enterprise.fleet_enforcement import _tenant_slug_for_ref
from nimbusware_api.routes.enterprise.iam_audit import log_fleet_policy_updated
from nimbusware_orchestrator.fleet_policies import (
    VALID_DISCOVERY_FIELD_IDS,
    FleetDiscoveryPolicy,
    load_fleet_discovery_policies,
    save_fleet_discovery_policies,
    tenant_discovery_policy,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class FleetDiscoveryPolicyBody(BaseModel):
    discovery_required_fields: list[str] = Field(default_factory=list, max_length=12)


@router.get("/tenants/{tenant_ref}/discovery-policy")
def get_fleet_discovery_policy(
    tenant_ref: str,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    return tenant_discovery_policy(slug).to_dict()


@router.put("/tenants/{tenant_ref}/discovery-policy")
def put_fleet_discovery_policy(
    tenant_ref: str,
    body: FleetDiscoveryPolicyBody,
    _: EnterpriseDep,
    iam: IamStoreDep,
    __: AdminDep,
) -> dict[str, Any]:
    slug = _tenant_slug_for_ref(iam, tenant_ref)
    fields = tuple(
        str(item).strip()
        for item in body.discovery_required_fields
        if str(item).strip() in VALID_DISCOVERY_FIELD_IDS
    )
    policies = load_fleet_discovery_policies()
    policies[slug] = FleetDiscoveryPolicy(
        tenant_slug=slug,
        discovery_required_fields=fields,
    )
    save_fleet_discovery_policies(policies)
    log_fleet_policy_updated(iam, tenant_slug=slug, policy_kind="discovery")
    saved: FleetDiscoveryPolicy = policies[slug]
    return saved.to_dict()
