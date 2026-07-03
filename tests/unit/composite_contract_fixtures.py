"""Raw event and gate payload dict builders for contract tests.

Use when asserting JSON/event shape without touching ``InMemoryEventStore``.
For typed store append sequences use :mod:`composite_store_fixtures`; for
on-disk YAML under a temp repo use :mod:`composite_repo_fixtures`.
"""

from __future__ import annotations

import base64
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

_ISO_NOW = "2026-05-12T12:34:56+00:00"
_ISO_LATER = "2026-05-12T12:35:00+00:00"

EVENT_TYPE_GATE = "gate.decision.emitted"
EVENT_TYPE_STAGE = "stage.started"
EVENT_TYPE_ESCALATED = "run.escalated"
EVENT_TYPE_FINDING = "finding.created"
EVENT_TYPE_RUN_CREATED = "run.created"

RID1 = UUID("11111111-1111-4111-8111-111111111111")
RID2 = UUID("22222222-2222-4222-8222-222222222222")
RID3 = UUID("33333333-3333-4333-8333-333333333333")
RID4 = UUID("44444444-4444-4444-8444-444444444444")


def gate_decision_event(
    *,
    event_id: UUID,
    metadata: Any,
    payload: Any,
    event_type: str = EVENT_TYPE_GATE,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def stage_started_event(
    *,
    event_id: UUID,
    payload: Any,
    metadata: Any = None,
    event_type: str = EVENT_TYPE_STAGE,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def run_escalated_event(
    *,
    event_id: UUID,
    payload: Any,
    event_type: str = EVENT_TYPE_ESCALATED,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "payload": payload,
    }


def finding_created_event(
    *,
    event_id: UUID,
    metadata: Any,
    payload: Any,
    event_type: str = EVENT_TYPE_FINDING,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def run_created_event(
    *,
    event_id: UUID,
    payload: Any,
    metadata: Any = None,
    event_type: str = EVENT_TYPE_RUN_CREATED,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


FINDING_CREATED = EVENT_TYPE_FINDING
SYNTHETIC_GATE_FAIL_CODE = "fo103_synthetic_fail"


def append_fail_gate(mem: Any, run_id: UUID, stage: str) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import (
        EventType,
        GateDecisionEmittedEvent,
        GateDecisionEmittedPayload,
        Verdict,
    )

    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage,
                verdict=Verdict.FAIL,
                failure_reason_code=SYNTHETIC_GATE_FAIL_CODE,
            ),
        ),
    )


def findings_for_run(mem: Any, run_id: UUID) -> list[dict[str, Any]]:
    return [r for r in mem.list_run_events(str(run_id)) if r.get("event_type") == FINDING_CREATED]


def stage_names_from_findings(findings: list[dict[str, Any]]) -> list[str | None]:
    return [(f.get("metadata") or {}).get("stage_name") for f in findings]


def append_uc_critique_fail_gates(mem: Any, run_id: UUID) -> None:
    from orchestrator.llm_plan import (
        IMPLEMENTATION_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
    )

    for stage in (
        IMPLEMENTATION_CRITIQUE_STAGE,
        TEST_WRITER_CRITIQUE_STAGE,
        PLANNER_CRITIQUE_STAGE,
    ):
        append_fail_gate(mem, run_id, stage)


def emit_critique_gate_fail_findings(
    orch: Any,
    mem: Any,
    run_id: UUID,
    *,
    env: dict[str, str] | None = None,
    eff: Any = None,
) -> list[dict[str, Any]]:
    import os
    from contextlib import nullcontext
    from unittest.mock import patch

    append_uc_critique_fail_gates(mem, run_id)
    ctx = patch.dict(os.environ, env, clear=False) if env else nullcontext()
    with ctx:
        if eff is not None:
            orch._maybe_emit_critique_gate_fail_findings(run_id, eff)  # noqa: SLF001
        else:
            orch._maybe_emit_critique_gate_fail_findings(run_id)  # noqa: SLF001
    return findings_for_run(mem, run_id)


def store_event_row(
    *,
    store_seq: int | str,
    event_type: str,
    occurred_at: Any = ...,
) -> dict[str, Any]:
    row: dict[str, Any] = {"store_seq": store_seq, "event_type": event_type}
    if occurred_at is not ...:
        row["occurred_at"] = occurred_at
    return row


def finding_dict_event(
    *,
    event_id: str = "ev-1",
    occurred_at: str = "2024-01-01T00:00:00Z",
    metadata: Any = None,
    payload: Any = None,
    event_type: str = EVENT_TYPE_FINDING,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": event_id,
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def urlsafe_b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def restore_b64_padding(value: str) -> str:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return value + pad


def set_mtime_days_ago(path: Path, *, days_ago: float) -> None:
    ts = time.time() - days_ago * 86400
    os.utime(path, (ts, ts))


def set_mtime_to(path: Path, when: datetime) -> None:
    ts = when.timestamp()
    os.utime(path, (ts, ts))
