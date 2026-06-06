"""Delivery backlog generation (stub and LLM modes)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogMetadata,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
    sync_backlog_metadata,
)
from agent_core.models.events_payloads import (
    DeliveryBacklogGeneratedPayload,
    DeliveryBacklogRevisedPayload,
)
from agent_core.models.events_records import (
    DeliveryBacklogGeneratedEvent,
    DeliveryBacklogRevisedEvent,
)


def _requirements_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            req = meta.get("requirements")
            if isinstance(req, dict):
                return req
        break
    return None


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


def generate_stub_backlog(
    campaign_id: str,
    *,
    requirements: dict[str, Any] | None = None,
    max_slices: int = 10,
) -> DeliveryBacklog:
    prompt = ""
    if isinstance(requirements, dict):
        prompt = str(requirements.get("business_prompt") or requirements.get("prompt") or "")
    title = "Campaign delivery"
    if prompt.strip():
        title = prompt.strip()[:120]
    count = max(1, min(max_slices, 10))
    default_paths = (
        "packages/nimbusware_orchestrator/micro_slice.py",
        "packages/nimbusware_orchestrator/slice_gate.py",
    )
    slices: list[BacklogSlice] = []
    for i in range(1, count + 1):
        sid = f"slice-stub-{i:03d}"
        deps: tuple[str, ...] = ()
        if i > 1:
            deps = (f"slice-stub-{i - 1:03d}",)
        slices.append(
            BacklogSlice(
                slice_id=sid,
                status=SliceStatus.PENDING,
                target_paths=default_paths,
                depends_on=deps,
                estimated_loc=80,
                rationale=f"Stub slice {i} for campaign: {title[:80]}",
            ),
        )
    backlog = DeliveryBacklog(
        campaign_id=campaign_id,
        epics=(
            BacklogEpic(
                epic_id="epic-stub",
                title=title,
                status=EpicStatus.IN_PROGRESS,
                features=(
                    BacklogFeature(
                        feature_id="feat-stub",
                        title="Stub feature scaffold",
                        acceptance_criteria=("All stub slices pass gate",),
                        slices=tuple(slices),
                    ),
                ),
            ),
        ),
        metadata=BacklogMetadata(generator_mode="stub"),
    )
    return sync_backlog_metadata(backlog)


def emit_backlog_generated(
    store: Any,
    run_id: UUID,
    backlog: DeliveryBacklog,
    *,
    generator_mode: str = "stub",
) -> None:
    store.append(
        DeliveryBacklogGeneratedEvent(
            event_type=EventType.DELIVERY_BACKLOG_GENERATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=DeliveryBacklogGeneratedPayload(
                campaign_id=backlog.campaign_id,
                backlog=backlog.model_dump(mode="json"),
                generator_mode=generator_mode,  # type: ignore[arg-type]
            ),
        ),
    )


def ensure_backlog(
    store: Any,
    run_id: UUID,
    rows: list[dict[str, Any]],
    *,
    generator_mode: str = "stub",
    max_slices: int = 10,
) -> DeliveryBacklog:
    existing = backlog_from_events(rows)
    if existing is not None:
        return apply_slice_outcomes(existing, rows)
    backlog = generate_stub_backlog(
        str(run_id),
        requirements=_requirements_from_rows(rows),
        max_slices=max_slices,
    )
    emit_backlog_generated(store, run_id, backlog, generator_mode=generator_mode)
    return backlog


def emit_backlog_revised(
    store: Any,
    run_id: UUID,
    backlog: DeliveryBacklog,
    *,
    revision_reason: str,
) -> None:
    store.append(
        DeliveryBacklogRevisedEvent(
            event_type=EventType.DELIVERY_BACKLOG_REVISED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=DeliveryBacklogRevisedPayload(
                campaign_id=backlog.campaign_id,
                revision_reason=revision_reason,
                backlog=backlog.model_dump(mode="json"),
            ),
        ),
    )
