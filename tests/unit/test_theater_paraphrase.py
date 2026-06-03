from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_projections.builders.theater_paraphrase import (
    apply_theater_paraphrase,
    theater_llm_summary_enabled,
)


def test_theater_llm_summary_disabled_by_default() -> None:
    run_id = uuid4()
    row = RunCreatedEvent(
        event_type=EventType.RUN_CREATED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        payload=RunCreatedPayload(
            workflow_profile="micro_slice",
            policy_version="1",
            config_snapshot_id="x",
        ),
    ).model_dump(mode="json")
    assert theater_llm_summary_enabled([row]) is False
    msgs = [{"headline": "a"}]
    assert apply_theater_paraphrase(msgs, enabled=False) == msgs


def test_theater_llm_summary_enabled_from_metadata() -> None:
    run_id = uuid4()
    row = RunCreatedEvent(
        event_type=EventType.RUN_CREATED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        payload=RunCreatedPayload(
            workflow_profile="micro_slice",
            policy_version="1",
            config_snapshot_id="x",
        ),
        metadata={"theater": {"llm_summary": True}},
    ).model_dump(mode="json")
    assert theater_llm_summary_enabled([row]) is True
