"""Continuous improvement council — vote on improvement track."""

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

    ws = Path(workspace)
    inventory = build_repo_inventory(ws)
    votes: list[CouncilVote] = []
    if inventory.orphan_count > 0:
        votes.append(
            CouncilVote(
                ImprovementTrack.SIMPLIFY,
                0.8,
                f"{inventory.orphan_count} orphan modules",
            ),
        )
    if inventory.duplicate_clusters > 0:
        votes.append(
            CouncilVote(
                ImprovementTrack.SIMPLIFY,
                0.7,
                f"{inventory.duplicate_clusters} duplicate clusters",
            ),
        )
    if inventory.cohesion_proposals > 5:
        votes.append(
            CouncilVote(
                ImprovementTrack.REFACTOR_COHESION,
                0.6,
                "cohesion proposals available",
            ),
        )
    if not votes:
        votes.append(
            CouncilVote(ImprovementTrack.IMPLEMENT_PLANNED, 0.5, "default backlog track"),
        )
    selected = max(votes, key=lambda v: v.score).track
    return ImprovementCouncilResult(inventory=inventory, votes=votes, selected=selected)
