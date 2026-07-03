from __future__ import annotations

from pathlib import Path

from orchestrator.critique.simplification_metrics import ComplexityIndex
from orchestrator.improvement.improvement_council import run_improvement_council
from orchestrator.repo_intel.code_graph import build_code_graph
from orchestrator.repo_intel.cohesion_graph import build_cohesion_graph
from orchestrator.repo_intel.explorer import run_repo_explore
from orchestrator.repo_intel.inventory import build_repo_inventory, inventory_health_score
from orchestrator.repo_intel.orphan_index import build_orphan_report
from orchestrator.repo_intel.similarity_index import build_similarity_index


def test_code_graph_builds_nodes(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    pkg = ws / "src"
    pkg.mkdir(parents=True)
    (pkg / "main.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    graph = build_code_graph(ws)
    assert any(n.kind == "function" for n in graph.nodes)


def test_code_graph_import_edges(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "util.py").write_text("VALUE = 1\n", encoding="utf-8")
    (ws / "main.py").write_text("from util import VALUE\nx = VALUE\n", encoding="utf-8")
    graph = build_code_graph(ws)
    assert any(tgt == "util.py" for _src, tgt in graph.import_edges)


def test_repo_inventory_and_council(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    pkg = ws / "src"
    pkg.mkdir(parents=True)
    (pkg / "a.py").write_text("x = 1\n", encoding="utf-8")
    (pkg / "b.py").write_text("y = 2\n", encoding="utf-8")
    inventory = build_repo_inventory(ws)
    assert inventory.complexity.loc >= 2
    assert 0 <= inventory.health_score <= 100
    council = run_improvement_council(ws)
    assert council.selected is not None
    assert council.inventory.health_score == inventory.health_score


def test_inventory_health_score_penalizes_debt() -> None:
    healthy = inventory_health_score(
        simplicity=9.0,
        orphan_count=0,
        duplicate_clusters=0,
        cohesion_proposals=2,
        feature_depth=40.0,
    )
    stressed = inventory_health_score(
        simplicity=4.0,
        orphan_count=8,
        duplicate_clusters=4,
        cohesion_proposals=12,
        feature_depth=240.0,
    )
    assert healthy > stressed


def test_similarity_and_orphans(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "dup1.py").write_text("import json\na = 1\n", encoding="utf-8")
    (ws / "dup2.py").write_text("import json\na = 1\n", encoding="utf-8")
    sim = build_similarity_index(ws)
    orphans = build_orphan_report(ws)
    explore = run_repo_explore(ws)
    cohesion = build_cohesion_graph(ws)
    assert sim.clusters
    assert len(orphans.orphans) >= 0
    assert explore.graph is not None
    assert cohesion.proposals is not None
    assert any(f.kind == "module_deps" for f in explore.findings)


def test_complexity_index(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "long.py").write_text("print('x')\n" * 10, encoding="utf-8")
    idx = ComplexityIndex.from_workspace(ws)
    assert idx.loc >= 10
