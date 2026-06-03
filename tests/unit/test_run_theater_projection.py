from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    DomainCriticProposedEvent,
    DomainCriticProposedPayload,
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    RequiredFixArtifact,
    ResearchPatternIndexedEvent,
    ResearchPatternIndexedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    Severity,
    StitchAppliedEvent,
    StitchAppliedPayload,
    StitchFailedEvent,
    StitchFailedPayload,
    StitchPlanEmittedEvent,
    StitchPlanEmittedPayload,
    Verdict,
)
from nimbusware_projections.builders.run_theater import build_run_theater_messages


def _with_store_seq(rows: list[dict]) -> list[dict]:
    for i, row in enumerate(rows):
        row["store_seq"] = i + 1
    return rows


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
    msgs = build_run_theater_messages(_with_store_seq(rows))
    headlines = [m["headline"] for m in msgs]
    assert "Why another round?" in headlines


def test_theater_research_and_stitch_event_lines() -> None:
    run_id = uuid4()
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
        ResearchPatternIndexedEvent(
            event_type=EventType.RESEARCH_PATTERN_INDEXED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchPatternIndexedPayload(
                pattern_id="pat-auth",
                repo_url="https://github.com/example/auth",
                paths=["src/auth.py"],
                license="MIT",
                embedding_ref="emb-1",
            ),
        ).model_dump(mode="json"),
        DomainCriticProposedEvent(
            event_type=EventType.DOMAIN_CRITIC_PROPOSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=DomainCriticProposedPayload(
                critic_template="domain_compliance",
                allowed_domains=["payments"],
                blocking_authority="BLOCKING",
            ),
        ).model_dump(mode="json"),
        {
            "event_type": "transplant.candidate.selected",
            "event_id": str(uuid4()),
            "run_id": str(run_id),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "candidate_id": "cand-1",
                "source_kind": "oss",
                "license": "MIT",
                "compatibility_score": 0.9,
            },
        },
        StitchPlanEmittedEvent(
            event_type=EventType.STITCH_PLAN_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StitchPlanEmittedPayload(
                target_paths=["src/auth.py", "src/config.py"],
                source_manifest_id="manifest-1",
                wiring_delta_summary="Add imports for auth module",
            ),
        ).model_dump(mode="json"),
        StitchAppliedEvent(
            event_type=EventType.STITCH_APPLIED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StitchAppliedPayload(
                snapshot_ref="snap-before-apply",
                files_added=["src/auth.py"],
                deps_added=["pyjwt"],
            ),
        ).model_dump(mode="json"),
        StitchFailedEvent(
            event_type=EventType.STITCH_FAILED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StitchFailedPayload(
                reason_code="license_denied",
                rollback_snapshot_ref="snap-rollback",
            ),
        ).model_dump(mode="json"),
    ]
    msgs = build_run_theater_messages(_with_store_seq(rows))
    headlines = [m["headline"] for m in msgs]
    assert any(h.startswith("Pattern indexed:") for h in headlines)
    assert any("Domain critic proposed:" in h for h in headlines)
    assert any("Transplant candidate selected" in h for h in headlines)
    assert any(h.startswith("Stitch plan:") for h in headlines)
    assert any(h.startswith("Stitch applied:") for h in headlines)
    assert any(h.startswith("Stitch failed:") for h in headlines)
    stitch_msgs = [m for m in msgs if m.get("message_kind") == "stitch"]
    failed = next(m for m in stitch_msgs if "Stitch failed" in m["headline"])
    assert failed["severity"] == "block"
