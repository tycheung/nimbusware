"""Append-only evolution ledger via stage.passed events (propose → score → keep/reject)."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload


class EvolutionPhase(str, Enum):
    PROPOSED = "proposed"
    SCORED = "scored"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class EvolutionLayer(str, Enum):
    PROMPT = "prompt"
    SKILL = "skill"
    VARIANT = "variant"


STAGE_BY_PHASE: dict[EvolutionPhase, str] = {
    EvolutionPhase.PROPOSED: "evolution.proposed",
    EvolutionPhase.SCORED: "evolution.scored",
    EvolutionPhase.PROMOTED: "evolution.promoted",
    EvolutionPhase.REJECTED: "evolution.rejected",
}


def _run_id(run_id: UUID | str) -> UUID:
    return UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id


def emit_evolution_event(
    store: Any,
    run_id: UUID | str,
    *,
    phase: EvolutionPhase,
    layer: EvolutionLayer,
    artifact_id: str,
    detail: dict[str, Any] | None = None,
) -> str:
    stage_name = STAGE_BY_PHASE[phase]
    block: dict[str, Any] = {
        "phase": phase.value,
        "layer": layer.value,
        "artifact_id": artifact_id,
        "detail": detail or {},
    }
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=_run_id(run_id),
            occurred_at=datetime.now(timezone.utc),
            metadata={"evolution": block},
            payload=StagePassedPayload(stage_name=stage_name, duration_ms=0),
        ),
    )
    return stage_name


def evolution_timeline_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage_name") or "")
        if not stage.startswith("evolution."):
            continue
        meta = row.get("metadata")
        block = meta.get("evolution") if isinstance(meta, dict) else None
        if not isinstance(block, dict):
            block = {}
        out.append(
            {
                "stage_name": stage,
                "phase": block.get("phase") or stage.rsplit(".", 1)[-1],
                "layer": block.get("layer"),
                "artifact_id": block.get("artifact_id"),
                "detail": block.get("detail") or {},
                "event_id": row.get("event_id"),
                "occurred_at": row.get("occurred_at"),
            },
        )
    return out


def pending_proposals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Artifacts proposed but not yet promoted or rejected."""
    timeline = evolution_timeline_from_rows(rows)
    terminal: set[str] = set()
    proposed: dict[str, dict[str, Any]] = {}
    for entry in timeline:
        aid = str(entry.get("artifact_id") or "").strip()
        if not aid:
            continue
        phase = str(entry.get("phase") or "")
        if phase in ("promoted", "rejected"):
            terminal.add(aid)
            proposed.pop(aid, None)
        elif phase == "proposed" and aid not in terminal:
            proposed[aid] = entry
    return list(proposed.values())
