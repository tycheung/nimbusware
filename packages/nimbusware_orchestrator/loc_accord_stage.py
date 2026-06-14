from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import StagePassedPayload, StageStartedPayload
from nimbusware_orchestrator.resolution_council import loc_accord_for_findings

REFACTOR_LOC_ACCORD_STAGE = "refactor.loc_accord"
DEFAULT_LOC_BUDGET = 400


def evaluate_loc_accord(
    loc_delta: int,
    *,
    loc_budget: int = DEFAULT_LOC_BUDGET,
) -> bool:
    return loc_accord_for_findings([{"loc_delta": loc_delta}], loc_budget=loc_budget)


def emit_refactor_loc_accord_stage(
    store: Any,
    run_id: UUID | str,
    *,
    loc_delta: int,
    loc_budget: int = DEFAULT_LOC_BUDGET,
) -> bool:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    passed = evaluate_loc_accord(loc_delta, loc_budget=loc_budget)
    now = datetime.now(timezone.utc)
    meta = {
        "loc_delta": loc_delta,
        "loc_budget": loc_budget,
        "loc_accord": passed,
        "detail": "accord" if passed else "loc_budget_exceeded",
    }
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={"refactor_loc_accord": meta},
            payload=StageStartedPayload(stage_name=REFACTOR_LOC_ACCORD_STAGE, attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={"refactor_loc_accord": meta},
            payload=StagePassedPayload(stage_name=REFACTOR_LOC_ACCORD_STAGE, duration_ms=0),
        ),
    )
    return passed
