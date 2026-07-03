from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CodeGraphNode:
    path: str
    kind: str
    symbol: str | None = None


@dataclass
class CodeGraphIndex:
    nodes: list[CodeGraphNode] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
    import_edges: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [{"path": n.path, "kind": n.kind, "symbol": n.symbol} for n in self.nodes],
            "edges": [{"from": a, "to": b} for a, b in self.edges],
            "import_edges": [{"from": a, "to": b} for a, b in self.import_edges],
            "node_count": len(self.nodes),
        }


def _module_stem(rel: str) -> str:
    path = Path(rel)
    if path.name == "__init__.py":
        return ".".join(path.parts[:-1])
    return ".".join(path.with_suffix("").parts)


def _resolve_import_target(module_stem: str, node: ast.ImportFrom, ws: Path) -> str | None:
    parts = module_stem.split(".")
    if node.level:
        base = parts[: max(0, len(parts) - node.level + (0 if node.module else 1))]
        if node.module:
            base.extend(node.module.split("."))
        candidate = ".".join(p for p in base if p)
    elif node.module:
        candidate = node.module
    else:
        return None
    rel = candidate.replace(".", "/")
    for suffix in (".py", "/__init__.py"):
        target = f"{rel}{suffix}" if suffix.startswith("/") else f"{rel}{suffix}"
        if (ws / target).is_file():
            return target.replace("\\", "/")
    return None


def _collect_import_edges(
    tree: ast.AST, rel: str, module_stem: str, ws: Path
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                out.append((rel, f"import:{top}"))
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_import_target(module_stem, node, ws)
            if target:
                out.append((rel, target))
            if node.module:
                base = node.module.replace(".", "/")
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    sub_path = f"{base}/{alias.name}.py"
                    if (ws / sub_path).is_file():
                        out.append((rel, sub_path.replace("\\", "/")))
                    elif node.module:
                        out.append((rel, f"import:{node.module.split('.')[0]}"))
            elif node.module:
                out.append((rel, f"import:{node.module.split('.')[0]}"))
    return out


def build_code_graph(workspace: Path, *, max_files: int | None = None) -> CodeGraphIndex:
    if max_files is None:
        import os

        raw = os.environ.get("NIMBUSWARE_CODE_INTEL_MAX_FILES", "500").strip()
        try:
            max_files = max(50, int(raw))
        except ValueError:
            max_files = 500
    index = CodeGraphIndex()
    ws = workspace.resolve()
    count = 0
    for py_path in sorted(ws.rglob("*.py")):
        if count >= max_files:
            break
        if any(part.startswith(".") for part in py_path.parts):
            continue
        rel = str(py_path.relative_to(ws)).replace("\\", "/")
        index.nodes.append(CodeGraphNode(path=rel, kind="module"))
        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        module_stem = _module_stem(rel)
        index.import_edges.extend(_collect_import_edges(tree, rel, module_stem, ws))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                sym = f"{rel}::{node.name}"
                index.nodes.append(CodeGraphNode(path=rel, kind="function", symbol=node.name))
                index.edges.append((rel, sym))
            elif isinstance(node, ast.ClassDef):
                sym = f"{rel}::{node.name}"
                index.nodes.append(CodeGraphNode(path=rel, kind="class", symbol=node.name))
                index.edges.append((rel, sym))
        count += 1
    return index


def module_hash(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return hashlib.sha256(text.encode()).hexdigest()[:16]
