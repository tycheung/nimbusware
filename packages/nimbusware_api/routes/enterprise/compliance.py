from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.deps import IamStoreDep, StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_config.tenant_policy_store import audit_redaction, load_tenant_audit_policy
from nimbusware_orchestrator.enterprise_audit_export import audit_retention_days
from nimbusware_orchestrator.fleet_policies import load_fleet_autopilot_policies
from nimbusware_orchestrator.fleet_policies import load_fleet_commit_policies
from nimbusware_orchestrator.fleet_policies import load_fleet_enforcement_policies
from nimbusware_orchestrator.fleet_policies import load_fleet_slice_policies
from nimbusware_projections.builders.competitive_metrics import build_compliance_dashboard_metrics

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
    dashboard = build_compliance_dashboard_metrics(store)
    audit_policy = load_tenant_audit_policy("default")
    return audit_redaction(
        {
            "audit_retention_days": audit_retention_days(),
            "iam_action_count": iam_count,
            "event_row_count": event_count,
            "fleet_policy_counts": fleet,
            "tenant_count": len(iam.list_tenants()) if hasattr(iam, "list_tenants") else 0,
            "gate_pass_rate": dashboard.get("gate_pass_rate"),
            "gate_pass_count": dashboard.get("gate_pass_count"),
            "gate_fail_count": dashboard.get("gate_fail_count"),
            "slice_size_histogram": dashboard.get("slice_size_histogram"),
            "mean_slices_per_run": dashboard.get("mean_slices_per_run"),
            "completed_runs": dashboard.get("completed_runs"),
            "commit_stage_events": dashboard.get("commit_stage_events"),
            "runs_scanned": dashboard.get("runs_scanned"),
            "last_event_at": dashboard.get("last_event_at"),
            "audit_policy": audit_policy,
        },
    )
