"""Aggregate stitch transplant outcomes from append-only event rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal, cast

from agent_core.models import EventType, Verdict

TransplantOutcome = Literal["pass", "fail", "unknown"]


def fetch_stitch_analytics_event_rows(store: Any, *, limit_runs: int) -> list[dict[str, Any]]:
    cap = max(1, min(limit_runs, 5000))
    if hasattr(store, "list_all_event_rows"):
        all_rows = store.list_all_event_rows()
        by_run: dict[str, dict[str, Any]] = {}
        for row in all_rows:
            if str(row.get("event_type") or "") != EventType.STITCH_APPLIED.value:
                continue
            rid = str(row.get("run_id"))
            seq = int(row.get("store_seq") or 0)
            prev = by_run.get(rid)
            if prev is None or seq > int(prev.get("store_seq") or 0):
                by_run[rid] = row
        run_ids = sorted(
            by_run.keys(),
            key=lambda rid: int(by_run[rid].get("store_seq") or 0),
            reverse=True,
        )[:cap]
        if not run_ids:
            return []
        grouped = store.list_run_events_many(run_ids)
        out: list[dict[str, Any]] = []
        for rid in run_ids:
            out.extend(grouped.get(rid, []))
        return out
    fetcher = getattr(store, "list_stitch_analytics_event_rows", None)
    if callable(fetcher):
        return cast(list[dict[str, Any]], fetcher(cap))
    return []


def _outcome_after_stitch(rows: list[dict[str, Any]], *, after_seq: int) -> TransplantOutcome:
    for row in rows:
        seq = int(row.get("store_seq") or 0)
        if seq <= after_seq:
            continue
        et = str(row.get("event_type") or "")
        if et == EventType.STITCH_FAILED.value:
            return "fail"
        if et == EventType.GATE_DECISION_EMITTED.value:
            payload = row.get("payload")
            if isinstance(payload, dict):
                verdict = payload.get("verdict")
                if verdict == Verdict.PASS.value:
                    return "pass"
                if verdict == Verdict.FAIL.value:
                    return "fail"
        if et == EventType.RUN_FAILED.value:
            return "fail"
        if et == EventType.RUN_COMPLETED.value:
            return "pass"
    return "unknown"


def transplant_outcome_for_run(rows: list[dict[str, Any]]) -> TransplantOutcome | None:
    """Outcome after the last stitch.applied on this run, if any."""
    ordered = sorted(rows, key=lambda r: int(r.get("store_seq") or 0))
    stitch_seq: int | None = None
    for row in ordered:
        if str(row.get("event_type") or "") == EventType.STITCH_APPLIED.value:
            stitch_seq = int(row.get("store_seq") or 0)
    if stitch_seq is None:
        return None
    return _outcome_after_stitch(ordered, after_seq=stitch_seq)


def compute_stitch_transplant_stats(event_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in event_rows:
        run_id = row.get("run_id")
        if run_id is None:
            continue
        by_run[str(run_id)].append(row)

    runs_with_stitch = 0
    transplant_pass = 0
    transplant_fail = 0

    for rows in by_run.values():
        rows.sort(key=lambda r: int(r.get("store_seq") or 0))
        stitch_seq: int | None = None
        for row in rows:
            if str(row.get("event_type") or "") == EventType.STITCH_APPLIED.value:
                stitch_seq = int(row.get("store_seq") or 0)
        if stitch_seq is None:
            continue
        runs_with_stitch += 1
        outcome = _outcome_after_stitch(rows, after_seq=stitch_seq)
        if outcome == "pass":
            transplant_pass += 1
        elif outcome == "fail":
            transplant_fail += 1

    sample_size = transplant_pass + transplant_fail
    pass_rate_pct: float | None = None
    if sample_size > 0:
        pass_rate_pct = round(transplant_pass / sample_size * 100.0, 1)

    return {
        "runs_with_stitch": runs_with_stitch,
        "transplant_pass": transplant_pass,
        "transplant_fail": transplant_fail,
        "sample_size": sample_size,
        "pass_rate_pct": pass_rate_pct,
    }
