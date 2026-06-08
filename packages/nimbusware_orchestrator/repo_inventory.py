"""Repo health inventory for continuous improvement council."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.cohesion_graph import build_cohesion_graph
from nimbusware_orchestrator.orphan_index import build_orphan_report
from nimbusware_orchestrator.similarity_index import build_similarity_index
from nimbusware_orchestrator.simplification_metrics import ComplexityIndex, simplicity_score


@dataclass
class RepoInventory:
    complexity: ComplexityIndex
    simplicity: float
    orphan_count: int
    duplicate_clusters: int
    cohesion_proposals: int
    feature_breadth: int = 0
    feature_depth: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "complexity": {
                "file_count": self.complexity.file_count,
                "loc": self.complexity.loc,
                "avg_loc_per_file": self.complexity.avg_loc_per_file,
            },
            "simplicity_score": self.simplicity,
            "orphan_count": self.orphan_count,
            "duplicate_clusters": self.duplicate_clusters,
            "cohesion_proposals": self.cohesion_proposals,
            "feature_breadth": self.feature_breadth,
            "feature_depth": self.feature_depth,
        }


def build_repo_inventory(workspace: Path) -> RepoInventory:
    complexity = ComplexityIndex.from_workspace(workspace)
    orphans = build_orphan_report(workspace)
    similarity = build_similarity_index(workspace)
    cohesion = build_cohesion_graph(workspace)
    dupes = sum(1 for c in similarity.clusters if len(c.paths) > 1)
    breadth = complexity.file_count
    depth = round(complexity.loc / max(1, complexity.file_count), 2)
    return RepoInventory(
        complexity=complexity,
        simplicity=simplicity_score(complexity),
        orphan_count=len(orphans.orphans),
        duplicate_clusters=dupes,
        cohesion_proposals=len(cohesion.proposals),
        feature_breadth=breadth,
        feature_depth=depth,
    )
