from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.feature_gap_matrix import build_feature_gap_matrix
from nimbusware_orchestrator.improvement_council import ImprovementTrack, run_improvement_council


def test_feature_gap_matrix_detects_backlog_ready(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    campaign = ws / ".nimbusware" / "campaign"
    campaign.mkdir(parents=True)
    (campaign / "backlog.json").write_text(
        json.dumps({"slices": [{"id": "s1", "status": "ready"}]}),
        encoding="utf-8",
    )
    (ws / "main.py").write_text("print('hi')\n", encoding="utf-8")
    matrix = build_feature_gap_matrix(ws)
    assert matrix.backlog_ready == 1
    assert "backlog_ready" in matrix.gaps
    assert matrix.has_implement_gap


def test_improvement_council_prefers_implement_planned_on_gap(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    pkg = ws / "src"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (ws / "tests").mkdir()
    (ws / "tests" / "test_app.py").write_text(
        "def test_main():\n    assert True\n", encoding="utf-8"
    )
    campaign = ws / ".nimbusware" / "campaign"
    campaign.mkdir(parents=True)
    (campaign / "backlog.json").write_text(
        json.dumps({"slices": [{"id": "s1", "status": "ready"}, {"id": "s2", "status": "ready"}]}),
        encoding="utf-8",
    )
    council = run_improvement_council(ws)
    planned = [v for v in council.votes if v.track == ImprovementTrack.IMPLEMENT_PLANNED]
    assert planned
    assert planned[0].score >= 0.7
    assert council.feature_gap_matrix is not None
    assert council.feature_gap_matrix.get("backlog_ready") == 2
