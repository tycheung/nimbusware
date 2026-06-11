from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from agent_core.read.campaign import campaign_effective_from_rows
from nimbusware_projections.builders.backlog_tree import backlog_tree_from_events


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("payload"))


def campaign_progress_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    ce = campaign_effective_from_rows(events)
    if ce is None:
        return None
    state = "executing"
    for row in reversed(events):
        et = row.get("event_type")
        if et == EventType.CAMPAIGN_COMPLETED.value:
            state = "completed"
            break
        if et == EventType.CAMPAIGN_FAILED.value:
            state = "failed"
            break
        if et == EventType.CAMPAIGN_PAUSED.value:
            state = "paused"
            break
    current_slice = None
    for row in reversed(events):
        if row.get("event_type") == EventType.SLICE_QUEUED.value:
            payload = _payload(row)
            current_slice = payload.get("slice_id")
            break
    tree = backlog_tree_from_events(events)
    summary: dict[str, Any] = {}
    if isinstance(tree, dict):
        raw_summary = tree.get("summary")
        if isinstance(raw_summary, dict):
            summary = raw_summary
    policy = mapping_or_empty(ce.get("policy"))
    completed = int(summary.get("slices_completed", 0))
    refactor_every = int(policy.get("refactor_every_n_slices", 5) or 5)
    arch_every = int(policy.get("architecture_every_n_slices", 10) or 10)
    next_refactor = refactor_every - (completed % refactor_every) if refactor_every else None
    next_arch = arch_every - (completed % arch_every) if arch_every else None
    return {
        "campaign_id": events[0].get("run_id") if events else None,
        "state": state,
        "autonomous": bool(ce.get("autonomous")),
        "current_slice_id": current_slice,
        "slices_completed": completed,
        "slices_total": int(summary.get("total_slices", 0)),
        "next_maintenance": {
            "refactor_in_slices": next_refactor,
            "architecture_in_slices": next_arch,
        },
        "backlog_summary": summary,
    }
