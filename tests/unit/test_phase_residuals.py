from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent
from agent_core.models.events_payloads import RunCreatedPayload

from nimbusware_maker.deploy_pipeline_events import emit_deploy_approved
from nimbusware_maker.user_participant_context import (
    load_user_participant_context,
    save_user_participant_context,
)
from nimbusware_store.memory import InMemoryEventStore


def test_participant_context_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "nimbusware_maker.user_participant_context.find_repo_root",
        lambda: tmp_path,
    )
    saved = save_user_participant_context(
        "user-ctx",
        expertise_bullets=["API design", "Postgres"],
        repo_root=tmp_path,
    )
    assert saved["expertise_bullets"] == ["API design", "Postgres"]
    loaded = load_user_participant_context("user-ctx", repo_root=tmp_path)
    assert loaded["expertise_bullets"] == ["API design", "Postgres"]


def test_emit_deploy_approved_appends_stage() -> None:
    store = InMemoryEventStore()
    rid = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id=str(uuid4()),
            ),
        ),
    )
    emit_deploy_approved(store, rid)
    rows = store.list_run_events(str(rid))
    assert any(r.get("payload", {}).get("stage_name") == "deploy.approved" for r in rows)
