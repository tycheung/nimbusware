from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogSlice,
    DeliveryBacklog,
    SliceStatus,
    sync_backlog_metadata,
)


def campaign_effective_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            ce = meta.get("campaign_effective")
            if isinstance(ce, dict) and ce.get("enabled"):
                return ce
        break
    return None


def campaign_enabled_for_run(rows: list[dict[str, Any]]) -> bool:
    return campaign_effective_from_rows(rows) is not None


def backlog_from_events(rows: list[dict[str, Any]]) -> DeliveryBacklog | None:
    latest: dict[str, Any] | None = None
    for row in rows:
        et = row.get("event_type")
        if et not in (
            EventType.DELIVERY_BACKLOG_GENERATED.value,
            EventType.DELIVERY_BACKLOG_REVISED.value,
        ):
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("backlog"), dict):
            latest = payload["backlog"]
    if latest is None:
        return None
    return DeliveryBacklog.model_validate(latest)


def _slice_gate_outcomes(rows: list[dict[str, Any]]) -> dict[str, SliceStatus]:
    outcomes: dict[str, SliceStatus] = {}
    for row in rows:
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("stage_name") != "slice.gate":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        sid = meta.get("backlog_slice_id") or meta.get("slice_id")
        if not isinstance(sid, str) or not sid.strip():
            continue
        if meta.get("slice_gate_verdict") == "PASS":
            outcomes[sid] = SliceStatus.PASSED
        else:
            outcomes[sid] = SliceStatus.FAILED
    return outcomes


def apply_slice_outcomes(backlog: DeliveryBacklog, rows: list[dict[str, Any]]) -> DeliveryBacklog:
    outcomes = _slice_gate_outcomes(rows)
    if not outcomes:
        return backlog
    epics: list[BacklogEpic] = []
    for epic in backlog.epics:
        features: list[BacklogFeature] = []
        for feature in epic.features:
            slices: list[BacklogSlice] = []
            for sl in feature.slices:
                status = outcomes.get(sl.slice_id, sl.status)
                slices.append(sl.model_copy(update={"status": status}))
            features.append(feature.model_copy(update={"slices": tuple(slices)}))
        epics.append(epic.model_copy(update={"features": tuple(features)}))
    completed = sum(1 for s in outcomes.values() if s == SliceStatus.PASSED)
    meta = backlog.metadata.model_copy(update={"slices_completed": completed})
    return sync_backlog_metadata(
        backlog.model_copy(update={"epics": tuple(epics), "metadata": meta})
    )


def has_backlog_event(rows: list[dict[str, Any]]) -> bool:
    return backlog_from_events(rows) is not None
