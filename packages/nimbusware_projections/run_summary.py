"""Run list summary projection from replayed event rows."""

from __future__ import annotations

from typing import Any

from agent_core.models import (
    EventType,
    RunCreatedEvent,
    RunStartedEvent,
    validate_event_dict,
)
from agent_core.timeline_metadata import persona_assignment_from_run_created_metadata
from hermes_store.protocol import serialized_event_from_row

# ``build_run_summary`` status values for non-empty runs; ``GET /v1/runs?status=`` filters on these.
RUN_LIST_FILTER_STATUSES: frozenset[str] = frozenset({"created", "running", "terminal"})


def build_run_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive status summary from ``list_run_events`` rows (ordered by ``store_seq``)."""
    if not rows:
        return {
            "status": "unknown",
            "workflow_profile": None,
            "event_count": 0,
            "latest_event_type": "unknown",
            "terminal_event_type": None,
            "findings_count": 0,
            "has_escalation": False,
            "run_created_metadata": {},
            "persona_assignment": None,
        }
    workflow_profile: str | None = None
    terminal: str | None = None
    for r in rows:
        et = r["event_type"]
        if et == EventType.RUN_CREATED.value:
            d = serialized_event_from_row(r)
            ev = validate_event_dict(d)
            if isinstance(ev, RunCreatedEvent):
                workflow_profile = ev.payload.workflow_profile
        if et in (
            EventType.RUN_FAILED.value,
            EventType.RUN_COMPLETED.value,
        ):
            terminal = et
    latest_et = rows[-1]["event_type"]
    status = "running"
    if terminal:
        status = "terminal"
    elif any(r["event_type"] == EventType.RUN_STARTED.value for r in rows):
        status = "running"
    elif latest_et == EventType.RUN_CREATED.value:
        status = "created"
    findings_count = sum(1 for r in rows if r["event_type"] == EventType.FINDING_CREATED.value)
    escalated = any(r["event_type"] == EventType.RUN_ESCALATED.value for r in rows)
    run_created_metadata: dict[str, object] = {}
    persona_assignment: dict[str, Any] | None = None
    for r in rows:
        if r["event_type"] != EventType.RUN_CREATED.value:
            continue
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        if isinstance(ev, RunCreatedEvent):
            run_created_metadata = dict(ev.metadata)
            persona_assignment = persona_assignment_from_run_created_metadata(ev.metadata)
        break
    return {
        "status": status,
        "workflow_profile": workflow_profile,
        "event_count": len(rows),
        "latest_event_type": latest_et,
        "terminal_event_type": terminal,
        "findings_count": findings_count,
        "has_escalation": escalated,
        "run_created_metadata": run_created_metadata,
        "persona_assignment": persona_assignment,
    }


def run_has_started(rows: list[dict[str, Any]]) -> bool:
    for r in rows:
        if r["event_type"] != EventType.RUN_STARTED.value:
            continue
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        if isinstance(ev, RunStartedEvent):
            return True
    return False
