from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import (
    EventType,
    GateOverriddenEvent,
    GateOverriddenPayload,
    RunEscalatedEvent,
    RunEscalatedPayload,
    serialize_event_persistent,
    validate_event_dict,
)


def test_run_escalated_round_trip() -> None:
    rid = uuid4()
    ev = RunEscalatedEvent(
        event_type=EventType.RUN_ESCALATED,
        event_id=uuid4(),
        run_id=rid,
        occurred_at=datetime.now(timezone.utc),
        payload=RunEscalatedPayload(actor_id="human:1", reason_code="deadlock"),
    )
    d = serialize_event_persistent(ev)
    back = validate_event_dict(d)
    assert back.event_type == EventType.RUN_ESCALATED


def test_gate_overridden_round_trip() -> None:
    rid = uuid4()
    ev = GateOverriddenEvent(
        event_type=EventType.GATE_OVERRIDDEN,
        event_id=uuid4(),
        run_id=rid,
        occurred_at=datetime.now(timezone.utc),
        payload=GateOverriddenPayload(
            actor_id="human:1",
            reason_code="policy",
            stage_name="plan",
        ),
    )
    d = serialize_event_persistent(ev)
    back = validate_event_dict(d)
    assert back.event_type == EventType.GATE_OVERRIDDEN
