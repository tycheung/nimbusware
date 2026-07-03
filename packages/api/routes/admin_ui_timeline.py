from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException

from api.errors import problem
from projections.builders import (
    agent_evaluator_timeline_summary,
    integrator_gate_timeline_history,
    integrator_gate_timeline_summary,
    run_escalated_timeline_history,
    run_escalated_timeline_summary,
    security_scan_on_verify_timeline_summary,
    self_refinement_timeline_summary,
    universal_critique_timeline_summary,
)
from store.protocol import serialized_event_from_row


def timeline_events_from_store(store: Any, run_id: UUID) -> list[dict[str, Any]]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    events: list[dict[str, Any]] = []
    for row in rows:
        d = serialized_event_from_row(row)
        d["store_seq"] = int(row.get("store_seq") or 0)
        events.append(d)
    return events


def build_timeline_panels_payload(events: list[dict[str, Any]], *, run_id: UUID) -> dict[str, Any]:
    ig_hist = integrator_gate_timeline_history(events)
    re_hist = run_escalated_timeline_history(events)
    return {
        "run_id": str(run_id),
        "integrator_gate": integrator_gate_timeline_summary(events)
        or (ig_hist[-1] if ig_hist else None),
        "agent_evaluator": agent_evaluator_timeline_summary(events),
        "self_refinement": self_refinement_timeline_summary(events),
        "run_escalated": run_escalated_timeline_summary(events)
        or (re_hist[-1] if re_hist else None),
        "security_scan_on_verify": security_scan_on_verify_timeline_summary(events),
        "universal_critique": universal_critique_timeline_summary(events),
    }
