from __future__ import annotations

from pathlib import Path

from orchestrator.launch.launch_evaluator import evaluate_workspace_rubric


def test_launch_eval_passes_tiny_python_fixture() -> None:
    root = Path(__file__).resolve().parents[1] / "fixtures" / "repos" / "tiny_python_app"
    scorecard = evaluate_workspace_rubric(root, min_aggregate=4.0)
    assert scorecard.aggregate > 0
    assert scorecard.testability >= 3.0
