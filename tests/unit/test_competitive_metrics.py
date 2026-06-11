from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_core.models import (
    EventType,
    ResearchBriefApprovedEvent,
    ResearchBriefEmittedEvent,
    ResearchBriefEmittedPayload,
    ResearchBriefReviewPayload,
    RunCompletedEvent,
    RunCompletedPayload,
    RunCreatedEvent,
    RunCreatedPayload,
    StagePassedEvent,
    StagePassedPayload,
)
from nimbusware_projections.builders.competitive_metrics import build_competitive_summary
from nimbusware_store.memory import InMemoryEventStore


def _seq(rows: list[dict]) -> None:
    for i, row in enumerate(rows):
        row["store_seq"] = i + 1


def test_competitive_summary_slice_gate_and_slices() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 12, 5, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 1, 12, 10, 0, tzinfo=timezone.utc)
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=t0,
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id="x",
            ),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=t1,
            payload=StagePassedPayload(stage_name="slice.applied", duration_ms=1),
            metadata={"slice_id": "s1"},
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=t1,
            payload=StagePassedPayload(stage_name="slice.gate", duration_ms=1),
            metadata={"slice_id": "s1", "slice_gate_verdict": "PASS"},
        ),
    )
    store.append(
        RunCompletedEvent(
            event_type=EventType.RUN_COMPLETED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=t2,
            payload=RunCompletedPayload(summary="done"),
        ),
    )
    body = build_competitive_summary(store, limit_runs=10)
    gate = body["metrics"]["slice_gate_pass_rate"]
    assert gate["pass_count"] == 1
    assert gate["rate"] == 1.0
    slices = body["metrics"]["slices_per_completed_run"]
    assert slices["completed_runs"] == 1
    assert slices["mean_slices"] == 1.0
    intent = body["metrics"]["intent_to_first_slice_ms"]
    assert intent["sample_size"] == 1
    assert intent["mean_ms"] == 5 * 60 * 1000.0


def test_competitive_summary_research_utilization() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    events = [
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id="x",
            ),
        ),
        ResearchBriefEmittedEvent(
            event_type=EventType.RESEARCH_BRIEF_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            payload=ResearchBriefEmittedPayload(
                brief_kind="domain",
                domain_tag="auth",
                summary="patterns",
                artifact_id="brief-1",
                sources=[],
            ),
        ),
        ResearchBriefApprovedEvent(
            event_type=EventType.RESEARCH_BRIEF_APPROVED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            payload=ResearchBriefReviewPayload(
                artifact_id="brief-1",
                brief_kind="domain",
                notes="ok",
            ),
        ),
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=now,
            payload=StagePassedPayload(stage_name="plan", duration_ms=1),
        ),
    ]
    for ev in events:
        store.append(ev)
    util = build_competitive_summary(store, limit_runs=5)["metrics"]["research_brief_utilization"]
    assert util["plan_stage_count"] == 1
    assert util["plan_with_approved_brief"] == 1
    assert util["rate"] == 1.0


def test_competitive_summary_includes_swe_bench_json(tmp_path: Path) -> None:
    bench_dir = tmp_path / "benchmarks"
    bench_dir.mkdir()
    snap = {"ok": True, "pass_rate": 0.85, "mode": "run"}
    (bench_dir / "latest_swe_bench.json").write_text(json.dumps(snap), encoding="utf-8")
    store = InMemoryEventStore()
    body = build_competitive_summary(store, limit_runs=5, repo_root=tmp_path)
    assert body["metrics"]["swe_bench"] == snap


def test_competitive_summary_includes_factory_weekly_json(tmp_path: Path) -> None:
    bench_dir = tmp_path / "benchmarks"
    bench_dir.mkdir()
    snap = {"passed": True, "entry_count": 3, "pass_rate": 1.0}
    (bench_dir / "latest_factory_weekly.json").write_text(json.dumps(snap), encoding="utf-8")
    store = InMemoryEventStore()
    body = build_competitive_summary(store, limit_runs=5, repo_root=tmp_path)
    assert body["metrics"]["factory_weekly"] == snap
