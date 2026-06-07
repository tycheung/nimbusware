from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.launch_eval_catalog import attach_context_from_run
from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "launch_eval"


def test_launch_eval_golden_campaign_crm_replay() -> None:
    spec = json.loads((GOLDEN_ROOT / "golden_campaign_crm_replay.json").read_text(encoding="utf-8"))
    ws_name = str(spec["workspace_fixture"])
    root = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / ws_name
    rows = spec["run_events"]
    attach = attach_context_from_run(rows)
    expected = spec["expected_attach_context"]
    for key, value in expected.items():
        assert attach.get(key) == value
    assert "business_prompt" in attach
    scorecard = evaluate_workspace_rubric(root, min_aggregate=float(spec["min_aggregate"]))
    assert scorecard.aggregate >= float(spec["min_aggregate"])
    assert scorecard.testability >= float(spec["min_testability"])
    assert scorecard.security >= float(spec["min_security"])
    if "min_maturity" in spec:
        assert scorecard.maturity >= float(spec["min_maturity"])
    if "min_maintainability" in spec:
        assert scorecard.maintainability >= float(spec["min_maintainability"])
    if spec.get("require_passed"):
        assert scorecard.passed
