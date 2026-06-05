"""Aggregate operator competitive-metrics snapshot from recent run events."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_core.models import EventType
from nimbusware_projections.builders.maker_progress import _slice_gate_rows, _stage_name
from nimbusware_projections.builders.run_research import run_research_briefs_from_events
from nimbusware_research.stitch_outcome_stats import (
    compute_stitch_transplant_stats,
    fetch_stitch_analytics_event_rows,
)

_SLICE_APPLIED = "slice.applied"
_PLAN_STAGES = frozenset({"plan", "slice.plan"})


def _parse_ts(raw: object) -> datetime | None:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        text = raw.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def fetch_recent_run_event_rows(
    store: Any,
    *,
    limit_runs: int,
) -> tuple[list[dict[str, Any]], int]:
    cap = max(1, min(limit_runs, 5000))
    if not hasattr(store, "list_all_event_rows"):
        return [], 0
    all_rows = store.list_all_event_rows()
    created: list[tuple[int, str]] = []
    for row in all_rows:
        if str(row.get("event_type") or "") != EventType.RUN_CREATED.value:
            continue
        created.append((int(row.get("store_seq") or 0), str(row.get("run_id"))))
    created.sort(reverse=True)
    run_ids: list[str] = []
    seen: set[str] = set()
    for _seq, rid in created:
        if rid in seen:
            continue
        seen.add(rid)
        run_ids.append(rid)
        if len(run_ids) >= cap:
            break
    if not run_ids:
        return [], 0
    grouped = store.list_run_events_many(run_ids)
    out: list[dict[str, Any]] = []
    for rid in run_ids:
        out.extend(grouped.get(rid, []))
    return out, len(run_ids)


def _rows_by_run(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rid = row.get("run_id")
        if rid is not None:
            by_run[str(rid)].append(row)
    for run_rows in by_run.values():
        run_rows.sort(key=lambda r: int(r.get("store_seq") or 0))
    return by_run


def _slice_gate_pass_rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gates = _slice_gate_rows(rows)
    if not gates:
        return {"pass_count": 0, "fail_count": 0, "total": 0, "rate": None}
    pass_n = sum(1 for g in gates.values() if g.get("verdict") == "PASS")
    fail_n = sum(1 for g in gates.values() if g.get("verdict") == "FAIL")
    total = len(gates)
    rate = pass_n / total if total else None
    return {"pass_count": pass_n, "fail_count": fail_n, "total": total, "rate": rate}


def _slices_per_completed_run(by_run: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    counts: list[int] = []
    for run_rows in by_run.values():
        if not any(r.get("event_type") == EventType.RUN_COMPLETED.value for r in run_rows):
            continue
        applied = sum(
            1
            for r in run_rows
            if r.get("event_type") == EventType.STAGE_PASSED.value
            and _stage_name(r) == _SLICE_APPLIED
        )
        counts.append(applied)
    if not counts:
        return {"completed_runs": 0, "mean_slices": None, "sample": []}
    return {
        "completed_runs": len(counts),
        "mean_slices": sum(counts) / len(counts),
        "sample": counts[:20],
    }


def _intent_to_first_slice_ms(by_run: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    deltas: list[float] = []
    for run_rows in by_run.values():
        created_at: datetime | None = None
        first_applied: datetime | None = None
        for row in run_rows:
            et = str(row.get("event_type") or "")
            ts = _parse_ts(row.get("occurred_at"))
            if et == EventType.RUN_CREATED.value and created_at is None:
                created_at = ts
            if (
                et == EventType.STAGE_PASSED.value
                and _stage_name(row) == _SLICE_APPLIED
                and first_applied is None
            ):
                first_applied = ts
        if created_at and first_applied:
            deltas.append((first_applied - created_at).total_seconds() * 1000.0)
    if not deltas:
        return {"sample_size": 0, "mean_ms": None, "median_ms": None}
    ordered = sorted(deltas)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    return {
        "sample_size": len(deltas),
        "mean_ms": sum(deltas) / len(deltas),
        "median_ms": median,
    }


def _research_brief_utilization(by_run: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    plan_count = 0
    with_brief = 0
    for run_rows in by_run.values():
        for row in run_rows:
            if row.get("event_type") != EventType.STAGE_PASSED.value:
                continue
            sn = _stage_name(row)
            if sn not in _PLAN_STAGES:
                continue
            plan_count += 1
            seq = int(row.get("store_seq") or 0)
            prior = [r for r in run_rows if int(r.get("store_seq") or 0) < seq]
            briefs = run_research_briefs_from_events(prior).get("briefs") or []
            if any(b.get("status") == "approved" for b in briefs):
                with_brief += 1
    rate = with_brief / plan_count if plan_count else None
    return {
        "plan_stage_count": plan_count,
        "plan_with_approved_brief": with_brief,
        "rate": rate,
    }


def _load_swe_bench_snapshot(repo_root: Path | None) -> dict[str, Any] | None:
    if repo_root is None:
        return None
    path = repo_root / "benchmarks" / "latest_swe_bench.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def build_competitive_summary(
    store: Any,
    *,
    limit_runs: int = 500,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    rows, runs_scanned = fetch_recent_run_event_rows(store, limit_runs=limit_runs)
    by_run = _rows_by_run(rows)
    stitch_rows = fetch_stitch_analytics_event_rows(store, limit_runs=limit_runs)
    stitch_stats = compute_stitch_transplant_stats(stitch_rows)
    generated = datetime.now(timezone.utc).isoformat()
    return {
        "generated_at": generated,
        "limit_runs": limit_runs,
        "runs_scanned": runs_scanned,
        "snapshot": True,
        "metrics": {
            "slice_gate_pass_rate": _slice_gate_pass_rate(rows),
            "slices_per_completed_run": _slices_per_completed_run(by_run),
            "intent_to_first_slice_ms": _intent_to_first_slice_ms(by_run),
            "stitch_transplant": stitch_stats,
            "research_brief_utilization": _research_brief_utilization(by_run),
            "swe_bench": _load_swe_bench_snapshot(repo_root),
        },
        "sources": {
            "event_store": "recent_run_events",
            "stitch": "stitch.applied + downstream gate/run terminal",
            "swe_bench": "benchmarks/latest_swe_bench.json (optional, local)",
        },
    }
