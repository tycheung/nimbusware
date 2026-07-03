from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.code_graph import CodeGraphIndex, build_code_graph


@dataclass
class GraphToolResult:
    tool: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    detail: str = ""


def _graph(workspace: Path, *, max_files: int = 200) -> CodeGraphIndex:
    return build_code_graph(workspace, max_files=max_files)


def jump_to_def(workspace: Path, symbol_path: str) -> GraphToolResult:
    graph = _graph(workspace)
    path = symbol_path.replace("\\", "/").strip()
    matches = [n for n in graph.nodes if n.path == path or path in n.path]
    return GraphToolResult(
        tool="jump_to_def",
        ok=bool(matches),
        data={"matches": [{"path": n.path, "kind": n.kind} for n in matches[:10]]},
        detail="found" if matches else "not_found",
    )


def trace_call_chain(workspace: Path, start_path: str, *, depth: int = 3) -> GraphToolResult:
    graph = _graph(workspace)
    start = start_path.replace("\\", "/").strip()
    edges = [e for e in graph.edges if e[0] == start or start in e[0]][: depth * 5]
    return GraphToolResult(
        tool="trace_call_chain",
        ok=True,
        data={"edges": [{"from": a, "to": b} for a, b in edges]},
        detail=f"depth={depth}",
    )


def list_orphans(workspace: Path) -> GraphToolResult:
    from orchestrator.orphan_index import build_orphan_report

    report = build_orphan_report(workspace)
    return GraphToolResult(
        tool="list_orphans",
        ok=True,
        data={"orphans": report.orphans[:20], "count": len(report.orphans)},
    )


def list_module_deps(workspace: Path, module_path: str) -> GraphToolResult:
    import ast

    ws = workspace.resolve()
    rel = module_path.replace("\\", "/").strip()
    target = ws / rel
    if not target.is_file():
        return GraphToolResult(tool="list_module_deps", ok=False, detail="not_found")
    try:
        tree = ast.parse(target.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as exc:
        return GraphToolResult(tool="list_module_deps", ok=False, detail=str(exc))
    deps: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.append(node.module.split(".")[0])
    unique = sorted({d for d in deps if d})
    return GraphToolResult(
        tool="list_module_deps",
        ok=True,
        data={"module": rel, "dependencies": unique[:40]},
        detail=f"count={len(unique)}",
    )


def find_similar_symbols(workspace: Path, path: str) -> GraphToolResult:
    from orchestrator.similarity_index import build_similarity_index

    index = build_similarity_index(workspace)
    rel = path.replace("\\", "/").strip()
    clusters = [c for c in index.clusters if rel in c.paths or any(rel in p for p in c.paths)]
    return GraphToolResult(
        tool="find_similar_symbols",
        ok=True,
        data={
            "clusters": [{"hash": c.hash, "paths": c.paths[:10]} for c in clusters[:5]],
        },
    )


def run_graph_tool(workspace: Path, tool: str, **kwargs: Any) -> GraphToolResult:
    name = tool.strip().lower()
    if name == "jump_to_def":
        return jump_to_def(workspace, str(kwargs.get("path") or kwargs.get("symbol_path") or ""))
    if name == "trace_call_chain":
        return trace_call_chain(
            workspace,
            str(kwargs.get("path") or kwargs.get("start_path") or ""),
            depth=int(kwargs.get("depth") or 3),
        )
    if name == "list_orphans":
        return list_orphans(workspace)
    if name == "find_similar_symbols":
        return find_similar_symbols(workspace, str(kwargs.get("path") or ""))
    if name == "list_module_deps":
        return list_module_deps(
            workspace,
            str(kwargs.get("path") or kwargs.get("module_path") or ""),
        )
    return GraphToolResult(tool=name, ok=False, detail="unknown_tool")
