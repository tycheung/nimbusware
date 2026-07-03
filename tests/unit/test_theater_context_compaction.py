from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import EventType, StageStartedEvent, StageStartedPayload
from projections.builders.context_budget import estimate_context_budget
from projections.builders.run_theater import build_run_theater_messages


def test_theater_renders_campaign_context_compacted() -> None:
    run_id = uuid4()
    row = StageStartedEvent(
        event_type=EventType.STAGE_STARTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        metadata={
            "tokens_before": 12400,
            "tokens_after": 4100,
            "merged_handoff_count": 7,
            "compaction_trigger": "auto_handoff",
            "summary": "## Goal\nShip contacts API",
            "kept_event_seq_range": [10, 42],
        },
        payload=StageStartedPayload(stage_name="campaign.context.compacted", attempt=1),
    ).model_dump(mode="json")
    row["store_seq"] = 5
    msgs = build_run_theater_messages([row])
    assert msgs
    headline = msgs[0].get("headline") or ""
    assert "Context compacted" in headline
    assert "12.4k" in headline
    assert msgs[0].get("message_kind") == "context"
    assert msgs[0].get("data_testid") == "theater-context-compacted"


def test_context_budget_includes_last_compaction() -> None:
    run_id = uuid4()
    row = StageStartedEvent(
        event_type=EventType.STAGE_STARTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        metadata={
            "tokens_before": 8000,
            "tokens_after": 3000,
            "merged_handoff_count": 3,
            "compaction_trigger": "manual",
            "compaction_id": str(uuid4()),
            "summary": "merged",
        },
        payload=StageStartedPayload(stage_name="campaign.context.compacted", attempt=1),
    ).model_dump(mode="json")
    row["store_seq"] = 9
    budget = estimate_context_budget([row])
    last = budget.get("last_compaction")
    assert isinstance(last, dict)
    assert last.get("tokens_before") == 8000
    assert last.get("trigger") == "manual"
    assert last.get("store_seq") == 9


def test_theater_renders_compaction_reverted_line() -> None:
    run_id = uuid4()
    row = StageStartedEvent(
        event_type=EventType.STAGE_STARTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        metadata={
            "compaction_id": str(uuid4()),
            "reverted_by": "operator",
            "reason": "too aggressive",
        },
        payload=StageStartedPayload(stage_name="campaign.context.compaction.reverted", attempt=1),
    ).model_dump(mode="json")
    row["store_seq"] = 11
    msgs = build_run_theater_messages([row])
    assert any(m.get("data_testid") == "theater-context-compaction-reverted" for m in msgs)
