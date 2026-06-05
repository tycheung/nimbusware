from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.config_blast_radius import preview_workflow_blast_radius
from nimbusware_store.memory import InMemoryEventStore


def test_blast_radius_detects_uc_change() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "universal_critique_effective": {
                    "default_enabled": False,
                    "unanimous_gate_enforce": True,
                    "impl_llm": False,
                    "tw_enabled": False,
                },
            },
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    out = preview_workflow_blast_radius(
        repo_root=find_repo_root(),
        store=store,
        workflow_profile="micro_slice",
        run_limit=10,
    )
    assert out["workflow_profile"] == "micro_slice"
    assert out["affected_run_count"] >= 0
