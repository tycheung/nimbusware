from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    RequiredFixArtifact,
    RunCreatedEvent,
    RunCreatedPayload,
    Severity,
    Verdict,
)
from nimbusware_projections.builders.run_theater import build_run_theater_messages


def test_theater_includes_why_another_round_on_gate_fail() -> None:
    run_id = uuid4()
    role_id = uuid4()
    rows = [
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id="x",
            ),
        ).model_dump(mode="json"),
        CriticVerdictEmittedEvent(
            event_type=EventType.CRITIC_VERDICT_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=CriticVerdictEmittedPayload(
                critic_role=role_id,
                verdict=Verdict.FAIL,
                severity=Severity.MEDIUM,
                owner_role=role_id,
                is_in_domain=True,
                required_fixes=[
                    RequiredFixArtifact(
                        format="json_patch",
                        target_files=["src/a.py"],
                        patch_artifact="[]",
                        validation_steps=["pytest"],
                        acceptance_criteria="tests pass",
                    ),
                ],
            ),
        ).model_dump(mode="json"),
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="verify",
                verdict=Verdict.FAIL,
                failure_reason_code="critic_fail",
            ),
        ).model_dump(mode="json"),
    ]
    for i, row in enumerate(rows):
        row["store_seq"] = i + 1
    msgs = build_run_theater_messages(rows)
    headlines = [m["headline"] for m in msgs]
    assert "Why another round?" in headlines
