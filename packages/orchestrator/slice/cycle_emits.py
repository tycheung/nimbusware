from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from orchestrator.improvement.resolution_council import ResolutionCouncilResult


def _run_id(run_id: UUID | str) -> UUID:
    return UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id


def _append_stage_passed(
    store: Any,
    run_id: UUID | str,
    *,
    stage_name: str,
    metadata: dict[str, Any],
) -> None:
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=_run_id(run_id),
            occurred_at=datetime.now(timezone.utc),
            metadata=metadata,
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=0),
        ),
    )


def emit_resolution_council(
    store: Any,
    run_id: UUID | str,
    resolution: ResolutionCouncilResult,
) -> None:
    _append_stage_passed(
        store,
        run_id,
        stage_name="resolution.council",
        metadata={"resolution_council": resolution.to_dict()},
    )


def emit_repo_explore(store: Any, run_id: UUID | str, result: Any) -> None:
    _append_stage_passed(
        store,
        run_id,
        stage_name="repo.explore",
        metadata={"repo_explore": result.to_dict()},
    )


def emit_improvement_council(store: Any, run_id: UUID | str, council: Any) -> None:
    _append_stage_passed(
        store,
        run_id,
        stage_name="improvement.council",
        metadata={"improvement_council": council.to_dict()},
    )


def emit_diagnose_learn(
    store: Any,
    run_id: UUID | str,
    *,
    slice_id: str,
    packet: dict[str, Any],
    fingerprint: str,
) -> None:
    _append_stage_passed(
        store,
        run_id,
        stage_name="diagnose.learn",
        metadata={
            "slice_id": slice_id,
            "diagnose_learn": {
                "fingerprint": fingerprint,
                "learning_available": packet.get("available"),
                "learning_path": packet.get("path") or packet.get("learning_path"),
                "excerpt": str(packet.get("excerpt") or "")[:2000],
            },
        },
    )
