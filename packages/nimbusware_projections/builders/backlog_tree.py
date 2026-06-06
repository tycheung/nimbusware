"""Project delivery backlog epic/feature/slice tree from campaign events."""

from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from agent_core.models.backlog import SliceStatus
from nimbusware_orchestrator.backlog_generator import apply_slice_outcomes, backlog_from_events


def backlog_tree_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    backlog = backlog_from_events(events)
    if backlog is None:
        return None
    backlog = apply_slice_outcomes(backlog, events)
    epics_out: list[dict[str, Any]] = []
    for epic in backlog.epics:
        features_out: list[dict[str, Any]] = []
        for feature in epic.features:
            slices_out = [
                {
                    "slice_id": sl.slice_id,
                    "status": sl.status.value,
                    "target_paths": list(sl.target_paths),
                    "depends_on": list(sl.depends_on),
                    "estimated_loc": sl.estimated_loc,
                    "rationale": sl.rationale,
                }
                for sl in feature.slices
            ]
            features_out.append(
                {
                    "feature_id": feature.feature_id,
                    "title": feature.title,
                    "acceptance_criteria": list(feature.acceptance_criteria),
                    "slices": slices_out,
                },
            )
        epics_out.append(
            {
                "epic_id": epic.epic_id,
                "title": epic.title,
                "status": epic.status.value,
                "features": features_out,
            },
        )
    pending = sum(
        1
        for epic in backlog.epics
        for feature in epic.features
        for sl in feature.slices
        if sl.status == SliceStatus.PENDING
    )
    passed = sum(
        1
        for epic in backlog.epics
        for feature in epic.features
        for sl in feature.slices
        if sl.status == SliceStatus.PASSED
    )
    return {
        "campaign_id": backlog.campaign_id,
        "metadata": backlog.metadata.model_dump(mode="json"),
        "completion_criteria": backlog.completion_criteria.model_dump(mode="json"),
        "epics": epics_out,
        "summary": {
            "total_slices": backlog.metadata.total_slices_planned,
            "slices_completed": passed,
            "slices_pending": pending,
        },
        "has_backlog": True,
    }


def campaign_has_backlog(events: list[dict[str, Any]]) -> bool:
    return any(
        r.get("event_type")
        in (
            EventType.DELIVERY_BACKLOG_GENERATED.value,
            EventType.DELIVERY_BACKLOG_REVISED.value,
        )
        for r in events
    )
