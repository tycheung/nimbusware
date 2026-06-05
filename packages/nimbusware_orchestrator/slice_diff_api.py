"""Resolve per-slice diff for public API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.micro_slice import SlicePlan, parse_slice_plan
from nimbusware_orchestrator.slice_diff import collect_slice_diff_stats


def slice_plans_from_events(events: list[dict[str, Any]]) -> list[SlicePlan]:
    """Chronological slice plans from ``slice.plan`` stage.started markers."""
    plans: list[SlicePlan] = []
    for row in events:
        if row.get("event_type") != "stage.started":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") != "slice.plan":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict) or not meta.get("slice_plan"):
            continue
        plans.append(
            parse_slice_plan(
                {
                    "slice_id": meta.get("slice_id"),
                    "rationale": meta.get("rationale"),
                    "target_paths": meta.get("target_paths"),
                    "acceptance_criteria": meta.get("acceptance_criteria"),
                },
            ),
        )
    return plans


def build_slice_diff_response(
    workspace: Path,
    events: list[dict[str, Any]],
    slice_index: int,
) -> dict[str, Any] | None:
    """Build diff payload for 1-based ``slice_index``; None if out of range."""
    if slice_index < 1:
        return None
    plans = slice_plans_from_events(events)
    if slice_index > len(plans):
        return None
    plan = plans[slice_index - 1]
    stats = collect_slice_diff_stats(workspace, plan)
    return {
        "slice_index": slice_index,
        "slice_id": plan.slice_id,
        "files": list(stats.changed_files),
        "unified_diff": stats.unified_diff,
        "stats": {
            "loc_added": stats.loc_added,
            "loc_removed": stats.loc_removed,
            "source": stats.source,
            "file_count": len(stats.changed_files),
        },
        "target_paths": list(plan.target_paths),
    }
