"""Pipeline micro-slice event recording."""

from __future__ import annotations
from nimbusware_env import find_repo_root

from pathlib import Path
from uuid import uuid4

from hermes_orchestrator.micro_slice import micro_slice_timeline_summary, parse_slice_plan
from hermes_orchestrator.pipeline import make_dev_orchestrator


def test_record_micro_slice_plan_and_gate() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    orch, store = make_dev_orchestrator(repo)
    run_id = orch.create_run("micro_slice")
    plan = parse_slice_plan(
        {
            "slice_id": "slice-test-1",
            "target_paths": ["packages/nimbusware_api/app.py"],
        },
    )
    orch.record_micro_slice_plan(run_id, plan)
    gate = orch.record_micro_slice_gate(
        run_id,
        plan,
        verify_ok=True,
        critique_verdicts=["PASS"],
        tests_passed=True,
    )
    assert gate.passed
    rows = store.list_run_events(str(run_id))
    events = [{"metadata": r.get("metadata") or {}} for r in rows]
    summary = micro_slice_timeline_summary(events)
    assert summary["slice_count_planned"] == 1
    assert summary["slices_completed"] == 1
