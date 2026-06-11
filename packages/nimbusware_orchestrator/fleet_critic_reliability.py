from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID, uuid4

from agent_core.mapping import mapping_or_empty


def _payload(ev: Mapping[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(ev.get("payload"))


def _is_in_domain(pl: Mapping[str, Any]) -> bool:
    raw = pl.get("is_in_domain")
    if raw is None:
        return True
    return bool(raw)


def critic_reliability_summary_from_events(events: Sequence[Any]) -> dict[str, Any]:
    critic_verdict_count = 0
    critic_fail_count = 0
    in_domain_verdict_count = 0
    in_domain_fail_count = 0
    out_of_domain_verdict_count = 0
    out_of_domain_fail_count = 0
    gate_block_count = 0
    finding_fingerprints: dict[str, int] = {}

    if not isinstance(events, list):
        events = []

    for ev in events:
        if not isinstance(ev, dict):
            continue
        et = str(ev.get("event_type") or "")
        pl = _payload(ev)
        if et == "critic.verdict.emitted":
            critic_verdict_count += 1
            in_domain = _is_in_domain(pl)
            is_fail = str(pl.get("verdict") or "").strip().upper() == "FAIL"
            if in_domain:
                in_domain_verdict_count += 1
                if is_fail:
                    in_domain_fail_count += 1
            else:
                out_of_domain_verdict_count += 1
                if is_fail:
                    out_of_domain_fail_count += 1
            if is_fail:
                critic_fail_count += 1
        elif et == "gate.decision.emitted":
            if str(pl.get("verdict") or "").strip().upper() == "FAIL":
                gate_block_count += 1
        elif et == "finding.created":
            stage = str(pl.get("stage_name") or pl.get("producer_stage") or "")
            msg = str(pl.get("message") or pl.get("summary") or "")[:80].strip().lower()
            key = f"{stage}|{msg}"
            if key.strip("|"):
                finding_fingerprints[key] = finding_fingerprints.get(key, 0) + 1

    repeat_paths = sum(1 for n in finding_fingerprints.values() if n > 1)
    fail_rate = critic_fail_count / critic_verdict_count if critic_verdict_count else 0.0
    in_domain_fail_rate = (
        in_domain_fail_count / in_domain_verdict_count if in_domain_verdict_count else 0.0
    )
    ood_rate = out_of_domain_verdict_count / critic_verdict_count if critic_verdict_count else 0.0
    return {
        "critic_verdict_count": critic_verdict_count,
        "critic_fail_count": critic_fail_count,
        "critic_fail_rate": round(fail_rate, 4),
        "in_domain_verdict_count": in_domain_verdict_count,
        "in_domain_fail_count": in_domain_fail_count,
        "in_domain_fail_rate": round(in_domain_fail_rate, 4),
        "out_of_domain_verdict_count": out_of_domain_verdict_count,
        "out_of_domain_fail_count": out_of_domain_fail_count,
        "out_of_domain_rate": round(ood_rate, 4),
        "gate_block_count": gate_block_count,
        "repeat_finding_paths": repeat_paths,
    }


def _tenant_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        tid = row.get("tenant_id")
        if tid is not None:
            return str(tid)
    return ""


def _merge_fleet_summary(totals: dict[str, Any], run_summary: dict[str, Any]) -> None:
    totals["runs_with_critics"] = int(totals.get("runs_with_critics", 0)) + (
        1 if int(run_summary.get("critic_verdict_count") or 0) > 0 else 0
    )
    totals["critic_verdict_count"] = int(totals.get("critic_verdict_count", 0)) + int(
        run_summary.get("critic_verdict_count") or 0,
    )
    totals["critic_fail_count"] = int(totals.get("critic_fail_count", 0)) + int(
        run_summary.get("critic_fail_count") or 0,
    )
    totals["gate_block_count"] = int(totals.get("gate_block_count", 0)) + int(
        run_summary.get("gate_block_count") or 0,
    )
    totals["repeat_finding_paths"] = int(totals.get("repeat_finding_paths", 0)) + int(
        run_summary.get("repeat_finding_paths") or 0,
    )


def _finalize_fleet_summary(totals: dict[str, Any], runs_scanned: int) -> dict[str, Any]:
    verdicts = int(totals.get("critic_verdict_count") or 0)
    fails = int(totals.get("critic_fail_count") or 0)
    fail_rate = fails / verdicts if verdicts else 0.0
    in_domain_verdicts = int(totals.get("in_domain_verdict_count") or 0)
    in_domain_fails = int(totals.get("in_domain_fail_count") or 0)
    in_domain_fail_rate = in_domain_fails / in_domain_verdicts if in_domain_verdicts else 0.0
    ood_verdicts = int(totals.get("out_of_domain_verdict_count") or 0)
    ood_rate = ood_verdicts / verdicts if verdicts else 0.0
    return {
        "tenant_id": totals.get("tenant_id", ""),
        "runs_scanned": runs_scanned,
        "runs_with_critics": int(totals.get("runs_with_critics") or 0),
        "critic_verdict_count": verdicts,
        "critic_fail_count": fails,
        "critic_fail_rate": round(fail_rate, 4),
        "in_domain_verdict_count": in_domain_verdicts,
        "in_domain_fail_count": in_domain_fails,
        "in_domain_fail_rate": round(in_domain_fail_rate, 4),
        "out_of_domain_verdict_count": ood_verdicts,
        "out_of_domain_fail_count": int(totals.get("out_of_domain_fail_count") or 0),
        "out_of_domain_rate": round(ood_rate, 4),
        "gate_block_count": int(totals.get("gate_block_count") or 0),
        "repeat_finding_paths": int(totals.get("repeat_finding_paths") or 0),
    }


def _scan_store_as_tenant(
    store: Any,
    tenant_id: UUID,
    run_limit: int,
) -> tuple[int, dict[str, Any]]:
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
    totals: dict[str, Any] = {"tenant_id": tid_s}
    for run_id in run_ids:
        rows = store.list_run_events(str(run_id))
        if not rows:
            continue
        if _tenant_from_rows(rows) and _tenant_from_rows(rows) != tid_s:
            continue
        runs_scanned += 1
        _merge_fleet_summary(totals, critic_reliability_summary_from_events(rows))
    return runs_scanned, totals


def tenant_critic_reliability_metrics(
    store: Any,
    *,
    tenant_id: UUID,
    run_limit: int = 100,
) -> dict[str, Any]:
    runs_scanned, totals = _scan_store_as_tenant(store, tenant_id, run_limit)
    return _finalize_fleet_summary(totals, runs_scanned)
