from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.routing import APIRouter as _APIRouter

from agent_core.models import serialize_event_persistent, validate_event_dict
from api.deps import StoreDep
from api.errors import problem
from console.integrator_gate._helpers import integrator_gate_from_timeline
from console.integrator_gate.latest_delta.exports import integrator_gate_summary_rows
from orchestrator.interjection_queue import queue_for_run
from orchestrator.interjection_slo import (
    interjection_slo_markdown,
    interjection_slo_summary,
)
from store.protocol import serialized_event_from_row

router: _APIRouter = APIRouter()


def _timeline_body_for_run(store: StoreDep, run_id: UUID) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    events: list[dict[str, Any]] = []
    for r in rows:
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        persisted = serialize_event_persistent(ev)
        persisted["store_seq"] = int(r.get("store_seq") or 0)
        events.append(persisted)
    return {"run_id": str(run_id), "events": events}


def _markdown_for_section(section: str, timeline_body: dict[str, Any]) -> str:
    key = section.strip().lower().replace("-", "_")
    if key == "integrator_gate":
        ig = integrator_gate_from_timeline(timeline_body)
        if not ig:
            return "No integrator gate summary for this run."
        summary_rows = integrator_gate_summary_rows(ig)
        lines = [f"- **{r.get('field', '')}**: {r.get('value', '')}" for r in summary_rows]
        return "\n".join(lines) if lines else "Integrator gate present (no summary rows)."
    if key == "events":
        n = len(timeline_body.get("events") or [])
        return f"**{n}** persisted events in the append-only store."
    if key == "interjection":
        events = timeline_body.get("events") or []
        run_id = str(timeline_body.get("run_id") or "")
        pending = 0
        if run_id:
            pending = int(queue_for_run(run_id).to_dict().get("count") or 0)
        summary = interjection_slo_summary(events, pending_queue_count=pending)
        return interjection_slo_markdown(summary, pending_queue_count=pending)
    return (
        f"Timeline section **{section}**. "
        f"Expand explainers in `timeline_explain.py` as Admin panels need them."
    )


@router.get("/runs/{run_id}/timeline/{section}/explain")
def get_timeline_section_explain(
    run_id: UUID,
    section: str,
    store: StoreDep,
) -> dict[str, Any]:
    timeline_body = _timeline_body_for_run(store, run_id)
    return {
        "run_id": str(run_id),
        "section": section,
        "markdown": _markdown_for_section(section, timeline_body),
        "event_count": len(timeline_body.get("events") or []),
    }
