from __future__ import annotations

from typing import Any
from uuid import UUID

_ISO_NOW = "2026-05-12T12:34:56+00:00"
_ISO_LATER = "2026-05-12T12:35:00+00:00"

EVENT_TYPE_GATE = "gate.decision.emitted"
EVENT_TYPE_STAGE = "stage.started"
EVENT_TYPE_ESCALATED = "run.escalated"
EVENT_TYPE_FINDING = "finding.created"
EVENT_TYPE_RUN_CREATED = "run.created"

RID1 = UUID("11111111-1111-4111-8111-111111111111")
RID2 = UUID("22222222-2222-4222-8222-222222222222")
RID3 = UUID("33333333-3333-4333-8333-333333333333")
RID4 = UUID("44444444-4444-4444-8444-444444444444")


def gate_decision_event(
    *,
    event_id: UUID,
    metadata: Any,
    payload: Any,
    event_type: str = EVENT_TYPE_GATE,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def stage_started_event(
    *,
    event_id: UUID,
    payload: Any,
    metadata: Any = None,
    event_type: str = EVENT_TYPE_STAGE,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def run_escalated_event(
    *,
    event_id: UUID,
    payload: Any,
    event_type: str = EVENT_TYPE_ESCALATED,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "payload": payload,
    }


def finding_created_event(
    *,
    event_id: UUID,
    metadata: Any,
    payload: Any,
    event_type: str = EVENT_TYPE_FINDING,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def run_created_event(
    *,
    event_id: UUID,
    payload: Any,
    metadata: Any = None,
    event_type: str = EVENT_TYPE_RUN_CREATED,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }
