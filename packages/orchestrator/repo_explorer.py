from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.code_graph import CodeGraphIndex, build_code_graph


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
    from orchestrator.repo_graph_tools import (
        find_similar_symbols,
        list_module_deps,
        list_orphans,
    )

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
    orphan_result = list_orphans(workspace)
    orphan_count = int(orphan_result.data.get("count") or 0)
    if orphan_count > 0:
        findings.append(
            RepoExploreFinding(
                kind="orphan_modules",
                message=f"{orphan_count} orphan module(s) detected",
                severity="info",
            ),
        )
    for node in module_nodes[:3]:
        sim = find_similar_symbols(workspace, node.path)
        clusters = sim.data.get("clusters") if isinstance(sim.data, dict) else None
        if isinstance(clusters, list) and clusters:
            findings.append(
                RepoExploreFinding(
                    kind="similar_symbols",
                    message=f"Similar symbols near {node.path}",
                    path=node.path,
                    severity="info",
                ),
            )
        deps = list_module_deps(workspace, node.path)
        dep_list = deps.data.get("dependencies") if isinstance(deps.data, dict) else None
        if isinstance(dep_list, list) and dep_list:
            findings.append(
                RepoExploreFinding(
                    kind="module_deps",
                    message=f"{len(dep_list)} import dep(s) in {node.path}",
                    path=node.path,
                    severity="info",
                ),
            )
    return RepoExploreResult(findings=findings, graph=graph)
