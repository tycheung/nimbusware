from __future__ import annotations

from typing import Any


def scope_snapshot_from_requirements(requirements: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(requirements, dict):
        return None
    manifest = requirements.get("stack_manifest")
    if not isinstance(manifest, dict):
        return None
    from nimbusware_orchestrator.binding_preflight import surface_stage_map

    return {
        "stack_manifest": manifest,
        "surface_stage_map": surface_stage_map(manifest),
        "discovery_summary": manifest.get("discovery_summary")
        if isinstance(manifest.get("discovery_summary"), dict)
        else {},
    }


def surface_outcomes_from_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from nimbusware_projections.builders.maker_progress import maker_progress_from_events

    progress = maker_progress_from_events(events)
    by_surface: dict[str, dict[str, Any]] = {}
    for row in progress.get("slices") or []:
        if not isinstance(row, dict):
            continue
        surface = str(row.get("surface_id") or "unknown").strip() or "unknown"
        bucket = by_surface.setdefault(
            surface,
            {"surface_id": surface, "slice_count": 0, "passed": 0, "failed": 0, "planned": 0},
        )
        bucket["slice_count"] += 1
        status = str(row.get("status") or "planned")
        if status == "passed":
            bucket["passed"] += 1
        elif status == "failed":
            bucket["failed"] += 1
        else:
            bucket["planned"] += 1
    return sorted(by_surface.values(), key=lambda r: str(r.get("surface_id", "")))
