from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from nimbusware_projections.builders.theater_paraphrase import (
    apply_theater_paraphrase,
    theater_enabled,
    theater_llm_summary_enabled,
    theater_max_message_chars,
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


def test_theater_disabled_from_metadata() -> None:
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
        metadata={"theater": {"enabled": False}},
    ).model_dump(mode="json")
    assert theater_enabled([row]) is False


def test_theater_max_message_chars_from_metadata() -> None:
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
        metadata={"theater": {"max_message_chars": 500}},
    ).model_dump(mode="json")
    assert theater_max_message_chars([row]) == 500
