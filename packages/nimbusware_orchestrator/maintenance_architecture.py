"""Periodic architecture maintenance passes during campaigns."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType
from agent_core.models.events_payloads import (
    MaintenanceArchitecturePassedPayload,
    MaintenanceArchitectureStartedPayload,
)
from agent_core.models.events_records import (
    MaintenanceArchitecturePassedEvent,
    MaintenanceArchitectureStartedEvent,
)


def should_run_architecture_pass(slices_completed: int, every_n: int) -> bool:
    return every_n > 0 and slices_completed > 0 and slices_completed % every_n == 0


def run_maintenance_architecture(
    orch: Any,
    run_id: UUID,
    *,
    slices_completed: int,
    can_revise_backlog: bool = True,
) -> bool:
    store = orch._store
    store.append(
        MaintenanceArchitectureStartedEvent(
            event_type=EventType.MAINTENANCE_ARCHITECTURE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=MaintenanceArchitectureStartedPayload(
                campaign_id=str(run_id),
                after_slice_count=slices_completed,
            ),
        ),
    )
    revised = False
    if can_revise_backlog:
        from agent_core.models.backlog import BacklogSlice, sync_backlog_metadata
        from nimbusware_orchestrator.backlog_generator import (
            backlog_from_events,
            emit_backlog_revised,
        )

        rows = store.list_run_events(str(run_id))
        backlog = backlog_from_events(rows)
        if backlog is not None:
            epics = list(backlog.epics)
            if epics and epics[0].features:
                feat = epics[0].features[0]
                arch_slice = BacklogSlice(
                    slice_id=f"arch-review-{slices_completed}",
                    rationale="Architecture pass follow-up slice",
                    target_paths=("packages/",),
                )
                feat = feat.model_copy(update={"slices": tuple(list(feat.slices) + [arch_slice])})
                epics[0] = epics[0].model_copy(update={"features": (feat,)})
                revised_backlog = sync_backlog_metadata(
                    backlog.model_copy(update={"epics": tuple(epics)})
                )
                emit_backlog_revised(
                    store,
                    run_id,
                    revised_backlog,
                    revision_reason="architecture_pass",
                )
                revised = True
    store.append(
        MaintenanceArchitecturePassedEvent(
            event_type=EventType.MAINTENANCE_ARCHITECTURE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=MaintenanceArchitecturePassedPayload(
                campaign_id=str(run_id),
                backlog_revised=revised,
            ),
        ),
    )
    return True
