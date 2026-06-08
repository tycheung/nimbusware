"""Call-chain cohesion scoring for module move proposals."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.code_graph import build_code_graph


@dataclass
class CohesionProposal:
    module: str
    score: float
    suggestion: str


@dataclass
class CohesionGraph:
    proposals: list[CohesionProposal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposals": [
                {"module": p.module, "score": p.score, "suggestion": p.suggestion}
                for p in self.proposals
            ]
        }


def build_cohesion_graph(workspace: Path) -> CohesionGraph:
    graph = build_code_graph(workspace)
    edge_counts: dict[str, int] = {}
    for src, _dst in graph.edges:
        edge_counts[src] = edge_counts.get(src, 0) + 1
    proposals: list[CohesionProposal] = []
    for module, count in sorted(edge_counts.items(), key=lambda x: -x[1])[:20]:
        score = min(1.0, count / 10.0)
        suggestion = "keep" if score >= 0.5 else "consider_split_or_move"
        proposals.append(
            CohesionProposal(module=module, score=round(score, 3), suggestion=suggestion)
        )
    return CohesionGraph(proposals=proposals)
