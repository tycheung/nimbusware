from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from orchestrator.repo_intel.inventory import RepoInventory, build_repo_inventory


class ImprovementTrack(str, Enum):
    IMPLEMENT_PLANNED = "implement_planned"
    DISCOVER_FEATURES = "discover_features"
    SIMPLIFY = "simplify"
    IMPROVE_COVERAGE = "improve_coverage"
    REFACTOR_COHESION = "refactor_cohesion"
    VARIANT_EXPERIMENT = "variant_experiment"
    RESEARCH_TRANSPLANT = "research_transplant"


@dataclass
class CouncilVote:
    track: ImprovementTrack
    score: float
    rationale: str


@dataclass
class ImprovementCouncilResult:
    inventory: RepoInventory
    votes: list[CouncilVote] = field(default_factory=list)
    selected: ImprovementTrack | None = None
    feature_gap_matrix: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "inventory": self.inventory.to_dict(),
            "votes": [
                {"track": v.track.value, "score": v.score, "rationale": v.rationale}
                for v in self.votes
            ],
            "selected": self.selected.value if self.selected else None,
        }
        if self.feature_gap_matrix is not None:
            payload["feature_gap_matrix"] = self.feature_gap_matrix
        return payload


def run_improvement_council(workspace: Path) -> ImprovementCouncilResult:
    from orchestrator.improvement.feature_gap_matrix import build_feature_gap_matrix
    from orchestrator.improvement.improvement_scope import filter_votes_by_scope, infer_repo_scope

    ws = workspace.resolve()
    inventory = build_repo_inventory(ws)
    gap_matrix = build_feature_gap_matrix(ws, inventory=inventory)
    health = inventory.health_score
    debt_boost = max(0.0, (70.0 - health) / 100.0)
    votes: list[CouncilVote] = []
    if inventory.orphan_count > 0:
        votes.append(
            CouncilVote(
                ImprovementTrack.SIMPLIFY,
                min(0.95, 0.55 + debt_boost + inventory.orphan_count * 0.05),
                f"{inventory.orphan_count} orphan modules (health={health})",
            ),
        )
    if inventory.duplicate_clusters > 0:
        votes.append(
            CouncilVote(
                ImprovementTrack.SIMPLIFY,
                min(0.9, 0.5 + debt_boost + inventory.duplicate_clusters * 0.08),
                f"{inventory.duplicate_clusters} duplicate clusters (health={health})",
            ),
        )
    if inventory.cohesion_proposals > 5:
        votes.append(
            CouncilVote(
                ImprovementTrack.REFACTOR_COHESION,
                min(0.85, 0.45 + debt_boost + inventory.cohesion_proposals * 0.02),
                f"{inventory.cohesion_proposals} cohesion proposals (health={health})",
            ),
        )
    from research.bundle_promotion import list_pending_stitch_catalog_candidates
    from research.pattern_index import pattern_index_path

    pending = list_pending_stitch_catalog_candidates(ws, limit=5)
    if gap_matrix.has_implement_gap and health >= 60:
        votes.append(
            CouncilVote(
                ImprovementTrack.IMPLEMENT_PLANNED,
                min(0.93, 0.7 + gap_matrix.backlog_ready * 0.05),
                f"feature gap matrix: {', '.join(gap_matrix.gaps)} (health={health})",
            ),
        )
    if health >= 75 and not pending and not gap_matrix.has_implement_gap:
        votes.append(
            CouncilVote(
                ImprovementTrack.IMPLEMENT_PLANNED,
                min(0.9, 0.45 + (health - 70.0) / 60.0),
                f"inventory healthy ({health}) — continue backlog",
            ),
        )
    if pending and health >= 50:
        votes.append(
            CouncilVote(
                ImprovementTrack.RESEARCH_TRANSPLANT,
                min(0.96, 0.9 + len(pending) * 0.02),
                f"{len(pending)} pending stitch catalog candidate(s) (health={health})",
            ),
        )
    pattern_path = pattern_index_path(ws)
    if pattern_path.is_file() and health >= 60 and inventory.orphan_count <= 3:
        try:
            import json

            loaded = json.loads(pattern_path.read_text(encoding="utf-8"))
            pattern_count = len(loaded) if isinstance(loaded, list) else 0
        except (OSError, json.JSONDecodeError):
            pattern_count = 0
        if pattern_count > 0 and not pending:
            votes.append(
                CouncilVote(
                    ImprovementTrack.RESEARCH_TRANSPLANT,
                    min(0.82, 0.52 + pattern_count * 0.04),
                    f"{pattern_count} indexed research pattern(s) (health={health})",
                ),
            )
    if not votes:
        votes.append(
            CouncilVote(ImprovementTrack.IMPLEMENT_PLANNED, 0.5, "default backlog track"),
        )
    scope = infer_repo_scope(
        loc=inventory.complexity.loc,
        orphan_count=inventory.orphan_count,
        duplicate_clusters=inventory.duplicate_clusters,
    )
    votes = filter_votes_by_scope(votes, scope)
    selected = max(votes, key=lambda v: v.score).track
    return ImprovementCouncilResult(
        inventory=inventory,
        votes=votes,
        selected=selected,
        feature_gap_matrix=gap_matrix.to_dict(),
    )
