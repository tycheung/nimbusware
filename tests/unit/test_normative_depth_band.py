from __future__ import annotations

from pathlib import Path

from orchestrator.improvement_council import CouncilVote, ImprovementTrack
from orchestrator.improvement_scope import (
    RepoScope,
    filter_votes_by_scope,
    infer_repo_scope,
)
from orchestrator.resolution_council import (
    loc_accord_for_findings,
    run_resolution_council,
)
from orchestrator.variant_arena import (
    create_variant_worktree,
    promote_variant_to_workspace,
    score_variant,
)


def test_loc_accord_budget() -> None:
    assert loc_accord_for_findings([{"loc_delta": 100}]) is True
    assert loc_accord_for_findings([{"loc_delta": 500}]) is False


def test_resolution_council_loc_budget_blocks_accord() -> None:
    result = run_resolution_council(
        findings=[{"kind": "lint", "message": "large change", "loc_delta": 900}],
        autopilot_level=9,
    )
    assert result.verdict.loc_accord is False
    assert result.verdict.accord is False
    assert result.verdict.detail == "loc_budget_exceeded"


def test_improvement_scope_filters_votes() -> None:
    votes = [
        CouncilVote(ImprovementTrack.VARIANT_EXPERIMENT, 0.9, "try variant"),
        CouncilVote(ImprovementTrack.SIMPLIFY, 0.5, "simplify"),
    ]
    filtered = filter_votes_by_scope(votes, RepoScope.GREENFIELD)
    assert all(
        v.track
        in {
            ImprovementTrack.VARIANT_EXPERIMENT,
            ImprovementTrack.DISCOVER_FEATURES,
            ImprovementTrack.IMPLEMENT_PLANNED,
        }
        for v in filtered
    )


def test_infer_repo_scope_greenfield() -> None:
    assert infer_repo_scope(loc=100, orphan_count=0, duplicate_clusters=0) == RepoScope.GREENFIELD


def test_promote_variant_to_workspace(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    (base / "app.py").write_text("x = 1\n", encoding="utf-8")
    variant_root = tmp_path / "variants"
    variant_root.mkdir()
    candidate = create_variant_worktree(base, variant_root, "alt")
    (candidate.workspace / "app.py").write_text("x = 2\n", encoding="utf-8")
    score_variant(candidate, tests_passed=True, loc_delta=0)
    assert promote_variant_to_workspace(candidate, base) is True
    assert "x = 2" in (base / "app.py").read_text(encoding="utf-8")
