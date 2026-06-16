"""Append ``gate.overridden`` for operator audit (no auto-unblock)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, GateOverriddenEvent, GateOverriddenPayload


def append_gate_overridden(
    store: Any,
    *,
    run_id: UUID,
    actor_id: str,
    reason_code: str,
    stage_name: str,
    policy_snapshot_id: str | None = None,
) -> None:
    store.append(
        GateOverriddenEvent(
            event_type=EventType.GATE_OVERRIDDEN,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateOverriddenPayload(
                actor_id=actor_id,
                reason_code=reason_code,
                stage_name=stage_name,
                policy_snapshot_id=policy_snapshot_id,
            ),
        ),
    )
