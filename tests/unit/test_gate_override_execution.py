from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_orchestrator.gate_override_execution import append_gate_overridden
from nimbusware_store.memory import InMemoryEventStore


def test_append_gate_overridden() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    append_gate_overridden(
        store,
        run_id=rid,
        actor_id="human:1",
        reason_code="manual",
        stage_name="slice.gate",
    )
    rows = store.list_run_events(str(rid))
    assert any(r.get("event_type") == EventType.GATE_OVERRIDDEN.value for r in rows)
