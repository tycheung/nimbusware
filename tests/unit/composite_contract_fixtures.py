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


FINDING_CREATED = EVENT_TYPE_FINDING
SYNTHETIC_GATE_FAIL_CODE = "fo103_synthetic_fail"


def append_fail_gate(mem: Any, run_id: UUID, stage: str) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import (
        EventType,
        GateDecisionEmittedEvent,
        GateDecisionEmittedPayload,
        Verdict,
    )

    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage,
                verdict=Verdict.FAIL,
                failure_reason_code=SYNTHETIC_GATE_FAIL_CODE,
            ),
        ),
    )


def findings_for_run(mem: Any, run_id: UUID) -> list[dict[str, Any]]:
    return [r for r in mem.list_run_events(str(run_id)) if r.get("event_type") == FINDING_CREATED]


def stage_names_from_findings(findings: list[dict[str, Any]]) -> list[str | None]:
    return [(f.get("metadata") or {}).get("stage_name") for f in findings]


def store_event_row(
    *,
    store_seq: int | str,
    event_type: str,
    occurred_at: Any = ...,
) -> dict[str, Any]:
    row: dict[str, Any] = {"store_seq": store_seq, "event_type": event_type}
    if occurred_at is not ...:
        row["occurred_at"] = occurred_at
    return row


def finding_dict_event(
    *,
    event_id: str = "ev-1",
    occurred_at: str = "2024-01-01T00:00:00Z",
    metadata: Any = None,
    payload: Any = None,
    event_type: str = EVENT_TYPE_FINDING,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": event_id,
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }
