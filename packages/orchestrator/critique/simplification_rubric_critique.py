from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent, StageStartedEvent
from agent_core.models.events_payloads import StagePassedPayload, StageStartedPayload
from orchestrator.repo_intel.inventory import RepoInventory, build_repo_inventory

SIMPLIFICATION_RUBRIC_STAGE = "simplification.rubric"
DEFAULT_HEALTH_FLOOR = 35.0


@dataclass(frozen=True)
class SimplificationRubricResult:
    passed: bool
    inventory: RepoInventory
    health_floor: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "health_floor": self.health_floor,
            "inventory": self.inventory.to_dict(),
        }


def run_simplification_rubric(
    workspace: Path,
    *,
    health_floor: float = DEFAULT_HEALTH_FLOOR,
) -> SimplificationRubricResult:
    inventory = build_repo_inventory(workspace)
    passed = inventory.health_score >= health_floor
    return SimplificationRubricResult(
        passed=passed,
        inventory=inventory,
        health_floor=health_floor,
    )


def emit_simplification_rubric_stage(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    health_floor: float = DEFAULT_HEALTH_FLOOR,
) -> SimplificationRubricResult:
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    result = run_simplification_rubric(workspace, health_floor=health_floor)
    now = datetime.now(timezone.utc)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            payload=StageStartedPayload(stage_name=SIMPLIFICATION_RUBRIC_STAGE, attempt=1),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=now,
            metadata={"simplification_rubric": result.to_dict()},
            payload=StagePassedPayload(stage_name=SIMPLIFICATION_RUBRIC_STAGE, duration_ms=0),
        ),
    )
    return result
