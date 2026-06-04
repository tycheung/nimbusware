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
    HardwareProfileDetectedEvent,
    HardwareProfileDetectedPayload,
    MemoryRetrievalEmittedEvent,
    MemoryRetrievalEmittedPayload,
    ModelPreflightPassedEvent,
    ModelPreflightPassedPayload,
    RequiredFixArtifact,
    ResearchBriefApprovedEvent,
    ResearchBriefEmittedEvent,
    ResearchBriefEmittedPayload,
    ResearchBriefReviewPayload,
    ResearchPatternIndexedEvent,
    ResearchPatternIndexedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    Severity,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
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


def test_theater_plan_stage_cites_approved_research() -> None:
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
        ResearchBriefEmittedEvent(
            event_type=EventType.RESEARCH_BRIEF_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefEmittedPayload(
                brief_kind="domain",
                domain_tag="auth",
                summary="OAuth integration patterns for the slice",
                artifact_id="brief-plan-1",
                sources=[],
            ),
        ).model_dump(mode="json"),
        ResearchBriefApprovedEvent(
            event_type=EventType.RESEARCH_BRIEF_APPROVED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefReviewPayload(
                artifact_id="brief-plan-1",
                brief_kind="domain",
                notes="approved",
            ),
        ).model_dump(mode="json"),
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StagePassedPayload(stage_name="plan", duration_ms=50),
        ).model_dump(mode="json"),
    ]
    msgs = build_run_theater_messages(_with_store_seq(rows))
    plan_msgs = [m for m in msgs if m.get("message_kind") == "plan"]
    assert plan_msgs
    body = plan_msgs[-1].get("body_md") or ""
    assert "brief-plan-1" in body
    assert "Approved research:" in body


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


def test_theater_governor_and_preflight_lines() -> None:
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
            metadata={"resource_governor": {"max_parallel_writers": 2, "hardware_tier": "medium"}},
        ).model_dump(mode="json"),
        ModelPreflightPassedEvent(
            event_type=EventType.MODEL_PREFLIGHT_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ModelPreflightPassedPayload(
                provider="ollama",
                validated_model_id="llama3",
                context_tokens=4096,
                p95_latency_ms=120,
            ),
        ).model_dump(mode="json"),
    ]
    msgs = build_run_theater_messages(_with_store_seq(rows))
    headlines = [m["headline"] for m in msgs]
    assert any("Resource governor" in h for h in headlines)
    assert any("Model preflight passed" in h for h in headlines)


def test_theater_hardware_profile_detected_line() -> None:
    run_id = uuid4()
    row = HardwareProfileDetectedEvent(
        event_type=EventType.HARDWARE_PROFILE_DETECTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        payload=HardwareProfileDetectedPayload(
            hardware_tier="medium",
            tier="medium",
        ),
    ).model_dump(mode="json")
    row["store_seq"] = 1
    msgs = build_run_theater_messages([row])
    assert any("Hardware profile detected (medium)" in m["headline"] for m in msgs)


def test_theater_metadata_deferral_line() -> None:
    run_id = uuid4()
    row = CriticVerdictEmittedEvent(
        event_type=EventType.CRITIC_VERDICT_EMITTED,
        event_id=uuid4(),
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        payload=CriticVerdictEmittedPayload(
            critic_role=uuid4(),
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=uuid4(),
            is_in_domain=True,
            required_fixes=[],
        ),
        metadata={
            "defer_to_role": {"role_id": "security-critic", "reason_code": "out_of_scope"},
        },
    ).model_dump(mode="json")
    row["store_seq"] = 1
    msgs = build_run_theater_messages([row])
    assert any("Deferring to security-critic" in m["headline"] for m in msgs)


def test_theater_slice_gate_and_memory_lines() -> None:
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
            metadata={"theater": {"enabled": True}},
        ).model_dump(mode="json"),
        MemoryRetrievalEmittedEvent(
            event_type=EventType.MEMORY_RETRIEVAL_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=MemoryRetrievalEmittedPayload(
                stage_name="plan",
                query_digest="abcd1234",
                hit_chunk_ids=["c1", "c2"],
                excerpt_chars=100,
                retrieval_k=2,
                repo_scope_hash="repo12345678",
            ),
        ).model_dump(mode="json"),
        StageFailedEvent(
            event_type=EventType.STAGE_FAILED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageFailedPayload(
                stage_name="slice.gate",
                reason_code="tests_failed",
                message="tests failed",
            ),
            metadata={
                "slice_id": "slice-1",
                "slice_gate_verdict": "FAIL",
                "slice_context_packet": {"test_output": "FAILED test_foo"},
            },
        ).model_dump(mode="json"),
    ]
    msgs = build_run_theater_messages(_with_store_seq(rows))
    headlines = [m["headline"] for m in msgs]
    assert any("Recalled 2 memory" in h for h in headlines)
    assert any("Slice gate blocked" in h for h in headlines)
