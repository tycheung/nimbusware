from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.code_graph import CodeGraphIndex, build_code_graph
from nimbusware_orchestrator.orphan_index import build_orphan_report

_CODE_INTEL_VERSION = 1
_REL_DIR = Path(".nimbusware/code_intel")


def workspace_fingerprint(workspace: Path) -> str:
    return hashlib.sha256(str(workspace.resolve()).encode()).hexdigest()[:16]


def code_intel_path(repo_root: Path, workspace: Path) -> Path:
    return repo_root / _REL_DIR / f"{workspace_fingerprint(workspace)}.json"


def compute_route_reachability(workspace: Path, graph: CodeGraphIndex) -> dict[str, Any]:
    ws = workspace.resolve()
    entries: list[str] = []
    for rel in ("main.py", "app.py"):
        if (ws / rel).is_file():
            entries.append(rel)
    for py in sorted(ws.rglob("app.py")):
        rel = str(py.relative_to(ws)).replace("\\", "/")
        if rel not in entries and "nimbusware_api" in rel.replace("\\", "/"):
            entries.append(rel)

    adj: dict[str, set[str]] = {}
    for src, tgt in graph.import_edges:
        if tgt.startswith("import:"):
            continue
        adj.setdefault(src, set()).add(tgt)

    reachable: set[str] = set()
    queue: deque[str] = deque(entries)
    while queue:
        mod = queue.popleft()
        if mod in reachable:
            continue
        reachable.add(mod)
        for nxt in adj.get(mod, ()):
            queue.append(nxt)

    modules = {n.path for n in graph.nodes if n.kind == "module"}
    unreachable = sorted(m for m in modules if m not in reachable and not m.endswith("__init__.py"))
    return {
        "entry_modules": entries,
        "reachable_module_count": len(reachable & modules),
        "unreachable_modules": unreachable[:50],
        "unreachable_count": len(unreachable),
    }


def build_code_intel_bundle(workspace: Path) -> dict[str, Any]:
    graph = build_code_graph(workspace)
    orphans = build_orphan_report(workspace, graph=graph)
    return {
        "version": _CODE_INTEL_VERSION,
        "workspace": str(workspace.resolve()),
        "graph": graph.to_dict(),
        "orphans": orphans.to_dict(),
        "route_reachability": compute_route_reachability(workspace, graph),
    }


def persist_code_intel(
    repo_root: Path, workspace: Path, bundle: dict[str, Any] | None = None
) -> Path:
    doc = bundle if bundle is not None else build_code_intel_bundle(workspace)
    path = code_intel_path(repo_root, workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


def load_code_intel(repo_root: Path, workspace: Path) -> dict[str, Any] | None:
    path = code_intel_path(repo_root, workspace)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def load_or_build_code_intel(repo_root: Path, workspace: Path) -> dict[str, Any]:
    cached = load_code_intel(repo_root, workspace)
    if cached is not None:
        return cached
    bundle = build_code_intel_bundle(workspace)
    persist_code_intel(repo_root, workspace, bundle)
    return bundle
