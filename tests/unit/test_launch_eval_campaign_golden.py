from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.launch.launch_eval_catalog import attach_context_from_run
from orchestrator.launch.launch_evaluator import evaluate_workspace_rubric

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "launch_eval"
REPOS_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repos"


def _manifest() -> dict[str, list[str]]:
    data = json.loads((GOLDEN_ROOT / "golden_replay_manifest.json").read_text(encoding="utf-8"))
    return {
        "campaign": list(data.get("campaign_goldens") or []),
        "workspace": list(data.get("workspace_goldens") or []),
    }


def _assert_campaign_golden(name: str) -> None:
    spec = json.loads((GOLDEN_ROOT / name).read_text(encoding="utf-8"))
    ws_name = str(spec["workspace_fixture"])
    root = REPOS_ROOT / ws_name
    attach = attach_context_from_run(spec["run_events"])
    for key, value in spec["expected_attach_context"].items():
        assert attach.get(key) == value
    scorecard = evaluate_workspace_rubric(root, min_aggregate=float(spec["min_aggregate"]))
    assert scorecard.aggregate >= float(spec["min_aggregate"])
    assert scorecard.testability >= float(spec["min_testability"])
    assert scorecard.security >= float(spec["min_security"])
    if spec.get("require_passed"):
        assert scorecard.passed


@pytest.mark.parametrize("golden_name", _manifest()["campaign"])
def test_launch_eval_campaign_golden_replay(golden_name: str) -> None:
    _assert_campaign_golden(golden_name)


def test_launch_eval_golden_replay_manifest_lists_known_files() -> None:
    manifest = _manifest()
    for name in manifest["campaign"]:
        assert (GOLDEN_ROOT / name).is_file(), name
    for name in manifest["workspace"]:
        assert (GOLDEN_ROOT / name).is_file(), name
