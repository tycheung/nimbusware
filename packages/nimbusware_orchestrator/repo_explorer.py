"""Repo exploration stage — graph-guided findings to backlog."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.code_graph import CodeGraphIndex, build_code_graph


@dataclass
class RepoExploreFinding:
    kind: str
    message: str
    path: str | None = None
    severity: str = "info"


@dataclass
class RepoExploreResult:
    findings: list[RepoExploreFinding] = field(default_factory=list)
    graph: CodeGraphIndex | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "kind": f.kind,
                    "message": f.message,
                    "path": f.path,
                    "severity": f.severity,
                }
                for f in self.findings
            ],
            "graph": self.graph.to_dict() if self.graph else None,
        }


def run_repo_explore(workspace: Path, *, max_files: int = 200) -> RepoExploreResult:
    graph = build_code_graph(workspace, max_files=max_files)
    findings: list[RepoExploreFinding] = []
    if len(graph.nodes) < 3:
        findings.append(
            RepoExploreFinding(
                kind="sparse_graph",
                message="Code graph has very few nodes",
                severity="info",
            ),
        )
    module_nodes = [n for n in graph.nodes if n.kind == "module"]
    if len(module_nodes) > max_files * 0.9:
        findings.append(
            RepoExploreFinding(
                kind="exploration_cap",
                message="Hit exploration file cap",
                severity="info",
            ),
        )
    return RepoExploreResult(findings=findings, graph=graph)
