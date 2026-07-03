from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, RunEscalatedEvent, RunEscalatedPayload
from orchestrator.escalation_policy_breadth import escalation_policy_breadth


def escalation_run_metadata(repo_root: Path) -> dict[str, Any]:
    """Attach policy breadth snapshot on ``run.escalated`` envelope metadata."""
    return {"escalation_policy_breadth": escalation_policy_breadth(repo_root)}


def append_run_escalated(
    store: Any,
    *,
    repo_root: Path,
    run_id: UUID,
    reason_code: str,
    notes: str | None = None,
    actor_id: str = "system:orchestrator",
) -> None:
    """Append ``run.escalated`` with breadth metadata for operator timelines."""
    meta = escalation_run_metadata(repo_root)
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata=meta,
            payload=RunEscalatedPayload(
                actor_id=actor_id,
                reason_code=reason_code,
                notes=notes,
            ),
        ),
    )
