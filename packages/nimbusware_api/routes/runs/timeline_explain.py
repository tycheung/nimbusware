from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.routing import APIRouter as _APIRouter

from agent_core.models import serialize_event_persistent, validate_event_dict
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_console.integrator_gate._helpers import integrator_gate_from_timeline
from nimbusware_console.integrator_gate.latest_delta.exports import integrator_gate_summary_rows
from nimbusware_store.protocol import serialized_event_from_row

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
