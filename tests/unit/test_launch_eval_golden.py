from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "launch_eval"


def test_launch_eval_golden_tiny_python_replay() -> None:
    spec = json.loads((GOLDEN_ROOT / "golden_tiny_python.json").read_text(encoding="utf-8"))
    ws_name = str(spec["workspace_fixture"])
    root = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / ws_name
    scorecard = evaluate_workspace_rubric(
        root,
        min_aggregate=float(spec["min_aggregate"]),
    )
    assert scorecard.aggregate >= float(spec["min_aggregate"])
    assert scorecard.testability >= float(spec["min_testability"])
    assert scorecard.security >= float(spec["min_security"])
    assert scorecard.maturity >= float(spec["min_maturity"])
    assert scorecard.maintainability >= float(spec["min_maintainability"])
    if spec.get("require_passed"):
        assert scorecard.passed
