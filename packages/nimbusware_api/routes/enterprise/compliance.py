from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.deps import IamStoreDep, StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_config.tenant_policy_store import audit_redaction
from nimbusware_orchestrator.enterprise_audit_export import audit_retention_days
from nimbusware_orchestrator.fleet_autopilot_policy import load_fleet_autopilot_policies
from nimbusware_orchestrator.fleet_commit_policy import load_fleet_commit_policies
from nimbusware_orchestrator.fleet_enforcement_policy import load_fleet_enforcement_policies
from nimbusware_orchestrator.fleet_slice_policy import load_fleet_slice_policies

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


@router.get("/compliance/summary")
def compliance_summary(
    _: EnterpriseDep,
    iam: IamStoreDep,
    store: StoreDep,
) -> dict[str, Any]:
    iam_count = 0
    if hasattr(iam, "list_iam_actions"):
        iam_count = len(iam.list_iam_actions())
    event_count = 0
    if hasattr(store, "list_all_event_rows"):
        event_count = len(store.list_all_event_rows())
    fleet = {
        "autopilot_tenants": len(load_fleet_autopilot_policies()),
        "enforcement_tenants": len(load_fleet_enforcement_policies()),
        "slice_tenants": len(load_fleet_slice_policies()),
        "commit_tenants": len(load_fleet_commit_policies()),
    }
    return audit_redaction(
        {
            "audit_retention_days": audit_retention_days(),
            "iam_action_count": iam_count,
            "event_row_count": event_count,
            "fleet_policy_counts": fleet,
            "tenant_count": len(iam.list_tenants()) if hasattr(iam, "list_tenants") else 0,
        },
    )
