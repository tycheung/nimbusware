from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo
from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


def test_launch_eval_rubric_after_micro_slice_apply(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "launch-ws")
    (ws / "packages/nimbusware_orchestrator").mkdir(parents=True, exist_ok=True)
    (ws / "packages/nimbusware_orchestrator/micro_slice.py").write_text(
        "# stub\n", encoding="utf-8"
    )
    (ws / "packages/nimbusware_orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")

    journey_client.attach_project(ws)
    journey_client.start_micro_slice_run(
        business_prompt="Build a minimal CRM with user authentication and contact list",
    )
    journey_client.approve_plan()
    prep = journey_client.prepare_slice()
    applied = journey_client.apply_slice(prep["pending"]["slice_id"])
    assert applied["status"] == "applied"

    scored = journey_client.client.post(f"/v1/runs/{journey_client.run_id}/maker/launch-eval")
    assert scored.status_code == 200, scored.text
    body = scored.json()
    assert body.get("attach_context", {}).get("prompt_id") == "basic_crm"

    scorecard = evaluate_workspace_rubric(ws, min_aggregate=0.0)
    assert scorecard.aggregate > 0
    assert scorecard.maturity >= 2.0
