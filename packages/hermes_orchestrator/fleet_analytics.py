from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4


def _tenant_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        tid = row.get("tenant_id")
        if tid is not None:
            return str(tid)
    return ""


def _gate_stats_from_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    passed = 0
    failed = 0
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("stage_name") != "slice.gate":
            continue
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        verdict = str(meta.get("slice_gate_verdict", "")).upper()
        if verdict == "PASS":
            passed += 1
        elif verdict == "FAIL":
            failed += 1
    return {
        "slice_gates_passed": passed,
        "slice_gates_failed": failed,
        "runs_with_gates": passed + failed,
    }


def _scan_store_as_tenant(
    store: Any, tenant_id: UUID, run_limit: int
) -> tuple[int, dict[str, int]]:
    from nimbusware_iam.context import get_auth_context, reset_auth_context, set_auth_context
    from nimbusware_iam.models import AuthContext

    prior = get_auth_context()
    set_auth_context(
        AuthContext(
            tenant_id=tenant_id,
            tenant_slug=str(tenant_id)[:8],
            key_id=uuid4(),
            role_taxonomy_keys=(),
            api_scopes=("maker_admin",),
        ),
    )
    try:
        run_ids = store.list_recent_run_ids(limit=run_limit)
    finally:
        if prior is None:
            reset_auth_context()
        else:
            set_auth_context(prior)
    tid_s = str(tenant_id)
    runs_scanned = 0
    totals = {"slice_gates_passed": 0, "slice_gates_failed": 0, "runs_with_gates": 0}
    for run_id in run_ids:
        rows = store.list_run_events(str(run_id))
        if not rows:
            continue
        if _tenant_from_rows(rows) and _tenant_from_rows(rows) != tid_s:
            continue
        runs_scanned += 1
        stats = _gate_stats_from_rows(rows)
        for key in totals:
            totals[key] += stats[key]
    return runs_scanned, totals


def tenant_run_metrics(
    store: Any,
    *,
    tenant_id: UUID,
    run_limit: int = 100,
) -> dict[str, Any]:
    runs_scanned, totals = _scan_store_as_tenant(store, tenant_id, run_limit)
    from hermes_orchestrator.fleet_ollama_sli import fleet_ollama_sli_status_snapshot

    sli = fleet_ollama_sli_status_snapshot()
    return {
        "tenant_id": str(tenant_id),
        "runs_scanned": runs_scanned,
        "gate_metrics": totals,
        "ollama_sli": {
            "sustained_p95_latency_ms": sli.get("sustained_p95_latency_ms"),
            "fleet_profile_enabled": sli.get("fleet_profile_enabled"),
        },
    }


def compare_tenant_metrics(
    store: Any,
    *,
    tenant_a: UUID,
    tenant_b: UUID,
    run_limit: int = 100,
) -> dict[str, Any]:
    a = tenant_run_metrics(store, tenant_id=tenant_a, run_limit=run_limit)
    b = tenant_run_metrics(store, tenant_id=tenant_b, run_limit=run_limit)
    return {
        "tenant_a": a,
        "tenant_b": b,
        "comparison": {
            "gate_pass_delta": (
                b["gate_metrics"]["slice_gates_passed"] - a["gate_metrics"]["slice_gates_passed"]
            ),
            "gate_fail_delta": (
                b["gate_metrics"]["slice_gates_failed"] - a["gate_metrics"]["slice_gates_failed"]
            ),
        },
    }
