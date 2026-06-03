from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import (
    EventType,
    ResearchBriefApprovedEvent,
    ResearchBriefEmittedEvent,
    ResearchBriefEmittedPayload,
    ResearchBriefReviewPayload,
)
from nimbusware_projections.builders.run_research import run_research_briefs_from_events


def test_run_research_briefs_status_from_review_events() -> None:
    run_id = uuid4()
    rows = [
        ResearchBriefEmittedEvent(
            event_type=EventType.RESEARCH_BRIEF_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefEmittedPayload(
                brief_kind="domain",
                domain_tag="auth",
                summary="OAuth patterns",
                artifact_id="brief-auth-1",
                sources=[],
            ),
        ).model_dump(mode="json"),
    ]
    rows[0]["store_seq"] = 1
    body = run_research_briefs_from_events(rows)
    assert body["count"] == 1
    assert body["briefs"][0]["status"] == "pending"

    rows.append(
        ResearchBriefApprovedEvent(
            event_type=EventType.RESEARCH_BRIEF_APPROVED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefReviewPayload(
                artifact_id="brief-auth-1",
                brief_kind="domain",
                notes="ok",
            ),
        ).model_dump(mode="json"),
    )
    rows[-1]["store_seq"] = 2
    body2 = run_research_briefs_from_events(rows)
    assert body2["briefs"][0]["status"] == "approved"
