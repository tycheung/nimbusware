from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, Verdict
from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogSlice,
    DeliveryBacklog,
    SliceStatus,
)
from agent_core.models.events_payloads import GateDecisionEmittedPayload
from agent_core.models.events_records import GateDecisionEmittedEvent
from env import find_repo_root
from maker.deploy_pipeline_events import emit_deploy_smoke_stages
from orchestrator.backlog_generator import emit_backlog_generated
from orchestrator.completion_evaluator import (
    evaluate_and_finalize_campaign,
    evaluate_completion,
)
from orchestrator.pipeline import make_dev_orchestrator


def _sample_passed_backlog(run_id: object) -> DeliveryBacklog:
    return DeliveryBacklog(
        campaign_id=str(run_id),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="E",
                features=(
                    BacklogFeature(
                        feature_id="f1",
                        title="F",
                        slices=(BacklogSlice(slice_id="s1", status=SliceStatus.PASSED),),
                    ),
                ),
            ),
        ),
    )


def _emit_verify_gate_pass(store: object, run_id: object) -> None:
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="slice.verify",
                verdict=Verdict.PASS,
            ),
        ),
    )


def test_evaluate_completion_incomplete_without_backlog() -> None:
    result = evaluate_completion([])
    assert result.verdict == "INCOMPLETE"


def test_evaluate_completion_pass_when_all_slices_passed() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    emit_backlog_generated(store, run_id, _sample_passed_backlog(run_id))
    _emit_verify_gate_pass(store, run_id)
    rows = store.list_run_events(str(run_id))
    result = evaluate_and_finalize_campaign(store, run_id, rows)
    assert result.verdict == "PASS"
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert EventType.CAMPAIGN_COMPLETED.value in types
    assert EventType.RUN_COMPLETED.value in types


def test_evaluate_completion_blocked_without_project_tests() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    emit_backlog_generated(store, run_id, _sample_passed_backlog(run_id))
    rows = store.list_run_events(str(run_id))
    result = evaluate_completion(rows)
    assert result.verdict == "INCOMPLETE"
    assert "project_tests_not_passed" in result.blocking_findings


def _deploy_requirements() -> dict[str, object]:
    return {
        "business_prompt": "Build and deploy a todo app",
        "stack_manifest": {
            "surfaces": ["api", "web", "deploy"],
            "stacks": {
                "api": "fastapi_python",
                "web": "react_vite",
                "deploy": "terraform_aws_ecs",
            },
            "confirmed": True,
        },
    }


def _deploy_passed_backlog(run_id: object) -> DeliveryBacklog:
    return DeliveryBacklog(
        campaign_id=str(run_id),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="E",
                features=(
                    BacklogFeature(
                        feature_id="f1",
                        title="F",
                        slices=(
                            BacklogSlice(
                                slice_id="s-api",
                                surface_id="api",
                                status=SliceStatus.PASSED,
                            ),
                            BacklogSlice(
                                slice_id="s-web",
                                surface_id="web",
                                status=SliceStatus.PASSED,
                            ),
                            BacklogSlice(
                                slice_id="s-deploy",
                                surface_id="deploy",
                                status=SliceStatus.PASSED,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_evaluate_completion_blocked_when_deploy_opted_in_without_smoke() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run(
        "campaign_micro_slice",
        requirements=_deploy_requirements(),
    )
    emit_backlog_generated(store, run_id, _deploy_passed_backlog(run_id))
    _emit_verify_gate_pass(store, run_id)
    rows = store.list_run_events(str(run_id))
    result = evaluate_completion(rows)
    assert result.verdict == "INCOMPLETE"
    assert "deploy_smoke_not_passed" in result.blocking_findings


def test_evaluate_completion_pass_when_deploy_opted_in_with_smoke() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run(
        "campaign_micro_slice",
        requirements=_deploy_requirements(),
    )
    emit_backlog_generated(store, run_id, _deploy_passed_backlog(run_id))
    _emit_verify_gate_pass(store, run_id)
    emit_deploy_smoke_stages(store, run_id, {"status": "passed", "detail": "smoke ok"})
    rows = store.list_run_events(str(run_id))
    result = evaluate_and_finalize_campaign(store, run_id, rows)
    assert result.verdict == "PASS"
    types = [r.get("event_type") for r in store.list_run_events(str(run_id))]
    assert EventType.CAMPAIGN_COMPLETED.value in types


def test_evaluate_completion_deep_eval_cadence_blocks_large_campaign() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("campaign_micro_slice")
    slices = tuple(BacklogSlice(slice_id=f"s{i}", status=SliceStatus.PASSED) for i in range(21))
    backlog = DeliveryBacklog(
        campaign_id=str(run_id),
        epics=(
            BacklogEpic(
                epic_id="e1",
                title="E",
                features=(BacklogFeature(feature_id="f1", title="F", slices=slices),),
            ),
        ),
    )
    emit_backlog_generated(store, run_id, backlog)
    _emit_verify_gate_pass(store, run_id)
    rows = store.list_run_events(str(run_id))
    result = evaluate_completion(rows)
    assert result.verdict == "INCOMPLETE"
    assert "deep_eval_cadence_pending" in result.blocking_findings
