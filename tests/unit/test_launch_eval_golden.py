from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.launch_evaluator import evaluate_workspace_rubric

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "launch_eval"


def test_launch_eval_golden_tiny_python_replay() -> None:
    _assert_golden_replay("golden_tiny_python.json", "tiny_python_app")


def test_launch_eval_golden_tiny_web_replay() -> None:
    _assert_golden_replay("golden_tiny_web.json", "tiny_web_app")


def _assert_golden_replay(golden_name: str, ws_name: str) -> None:
    spec = json.loads((GOLDEN_ROOT / golden_name).read_text(encoding="utf-8"))
    assert str(spec.get("workspace_fixture") or ws_name) == ws_name
    root = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / ws_name
    scorecard = evaluate_workspace_rubric(
        root,
        min_aggregate=float(spec["min_aggregate"]),
    )
    assert scorecard.aggregate >= float(spec["min_aggregate"])
    assert scorecard.testability >= float(spec["min_testability"])
    assert scorecard.security >= float(spec["min_security"])
    if "min_scalability" in spec:
        assert scorecard.scalability >= float(spec["min_scalability"])
    if "min_maturity" in spec:
        assert scorecard.maturity >= float(spec["min_maturity"])
    if "min_maintainability" in spec:
        assert scorecard.maintainability >= float(spec["min_maintainability"])
    if spec.get("require_passed"):
        assert scorecard.passed
