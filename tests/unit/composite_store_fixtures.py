"""Typed ``InMemoryEventStore`` append helpers for integration-style unit tests.

Use when the test exercises store read paths or projection rebuilds. For raw
event dict literals use :mod:`composite_contract_fixtures`; for workflow YAML on
disk use :mod:`composite_repo_fixtures`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    RunCompletedEvent,
    RunCompletedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    RunFailedEvent,
    RunFailedPayload,
    RunStartedEvent,
    RunStartedPayload,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
)
from store.memory import InMemoryEventStore

BACKEND_WRITER = UUID("44444444-4444-4444-8444-444444444404")


def make_store_and_run() -> tuple[InMemoryEventStore, UUID]:
    """Fresh ``InMemoryEventStore`` + a new run UUID for one axis."""
    return InMemoryEventStore(), uuid4()


def append_run_created(
    store: InMemoryEventStore,
    run_id: UUID,
    *,
    workflow_profile: str = "default",
    metadata: dict[str, Any] | None = None,
) -> None:
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile=workflow_profile,
                policy_version="1",
                config_snapshot_id="snap",
            ),
            metadata=metadata or {},
        ),
    )


def append_run_started(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunStartedEvent(
            event_type=EventType.RUN_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunStartedPayload(started_by="fo115_actor"),
        ),
    )


def append_run_failed(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunFailedEvent(
            event_type=EventType.RUN_FAILED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunFailedPayload(
                reason_code="fo115_reason",
                message="fo115 terminal failure",
            ),
        ),
    )


def append_run_completed(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunCompletedEvent(
            event_type=EventType.RUN_COMPLETED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCompletedPayload(summary="fo115 happy completion"),
        ),
    )


def append_run_escalated(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id="fo115_human",
                reason_code="fo115_escalation",
            ),
        ),
    )


def append_stage_started(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="fo115_stage", attempt=1),
        ),
    )


def append_finding_created(store: InMemoryEventStore, run_id: UUID) -> None:
    store.append(
        FindingCreatedEvent(
            event_type=EventType.FINDING_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=FindingCreatedPayload(
                finding_id=uuid4(),
                category="fo115_category",
                owner_role=BACKEND_WRITER,
                severity=Severity.LOW,
                source_artifact="fo115",
                repro_steps=[],
                required_fixes=[],
            ),
        ),
    )


def inject_raw_run_created_row(
    store: Any,
    run_id: UUID,
    *,
    workflow_profile: Any,
) -> None:
    store._seq += 1  # noqa: SLF001
    store._rows.append(  # noqa: SLF001
        {
            "store_seq": store._seq,  # noqa: SLF001
            "event_id": uuid4(),
            "run_id": run_id,
            "stage_id": None,
            "task_id": None,
            "event_type": "run.created",
            "event_version": 1,
            "occurred_at": datetime.now(timezone.utc),
            "correlation_id": None,
            "idempotency_key": None,
            "actor_role_id": None,
            "previous_event_id": None,
            "payload": {
                "workflow_profile": workflow_profile,
                "policy_version": "1",
                "config_snapshot_id": str(uuid4()),
            },
            "metadata": {},
        }
    )
