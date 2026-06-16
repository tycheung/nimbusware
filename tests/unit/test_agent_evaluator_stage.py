from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_extensions.phase2 import AgentEvaluator
from nimbusware_store.memory import InMemoryEventStore


def test_emit_evaluation_stage_started() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="default",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    AgentEvaluator().emit_evaluation_stage_started(store, run_id=run_id, persona_id="qa")
    last = store.list_run_events(str(run_id))[-1]
    assert last["event_type"] == "stage.started"
    assert last.get("payload", {}).get("stage_name") == "agent_eval:qa"
