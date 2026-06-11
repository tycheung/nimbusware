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
    health_score: float = 100.0

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
            "health_score": self.health_score,
        }


def inventory_health_score(
    *,
    simplicity: float,
    orphan_count: int,
    duplicate_clusters: int,
    cohesion_proposals: int,
    feature_depth: float,
) -> float:
    score = 100.0
    score -= min(30.0, float(orphan_count) * 3.0)
    score -= min(20.0, float(duplicate_clusters) * 5.0)
    score -= min(15.0, max(0, cohesion_proposals - 5) * 2.0)
    score -= max(0.0, 10.0 - simplicity) * 2.0
    if feature_depth > 200:
        score -= 10.0
    elif feature_depth > 120:
        score -= 5.0
    return round(max(0.0, min(100.0, score)), 1)


def build_repo_inventory(workspace: Path) -> RepoInventory:
    complexity = ComplexityIndex.from_workspace(workspace)
    orphans = build_orphan_report(workspace)
    similarity = build_similarity_index(workspace)
    cohesion = build_cohesion_graph(workspace)
    dupes = sum(1 for c in similarity.clusters if len(c.paths) > 1)
    breadth = complexity.file_count
    depth = round(complexity.loc / max(1, complexity.file_count), 2)
    simplicity = simplicity_score(complexity)
    orphans_n = len(orphans.orphans)
    cohesion_n = len(cohesion.proposals)
    health = inventory_health_score(
        simplicity=simplicity,
        orphan_count=orphans_n,
        duplicate_clusters=dupes,
        cohesion_proposals=cohesion_n,
        feature_depth=depth,
    )
    return RepoInventory(
        complexity=complexity,
        simplicity=simplicity,
        orphan_count=orphans_n,
        duplicate_clusters=dupes,
        cohesion_proposals=cohesion_n,
        feature_breadth=breadth,
        feature_depth=depth,
        health_score=health,
    )
