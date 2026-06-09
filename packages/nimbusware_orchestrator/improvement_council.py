from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nimbusware_orchestrator.repo_inventory import RepoInventory, build_repo_inventory


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "inventory": self.inventory.to_dict(),
            "votes": [
                {"track": v.track.value, "score": v.score, "rationale": v.rationale}
                for v in self.votes
            ],
            "selected": self.selected.value if self.selected else None,
        }


def run_improvement_council(workspace) -> ImprovementCouncilResult:
    from pathlib import Path

    from nimbusware_orchestrator.improvement_scope import filter_votes_by_scope, infer_repo_scope

    ws = Path(workspace)
    inventory = build_repo_inventory(ws)
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
    if health >= 75:
        votes.append(
            CouncilVote(
                ImprovementTrack.IMPLEMENT_PLANNED,
                min(0.9, 0.45 + (health - 70.0) / 60.0),
                f"inventory healthy ({health}) — continue backlog",
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
    return ImprovementCouncilResult(inventory=inventory, votes=votes, selected=selected)
