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

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [{"path": n.path, "kind": n.kind, "symbol": n.symbol} for n in self.nodes],
            "edges": [{"from": a, "to": b} for a, b in self.edges],
            "node_count": len(self.nodes),
        }


def build_code_graph(workspace: Path, *, max_files: int = 200) -> CodeGraphIndex:
    index = CodeGraphIndex()
    ws = workspace.resolve()
    count = 0
    for py_path in sorted(ws.rglob("*.py")):
        if count >= max_files:
            break
        if any(part.startswith(".") for part in py_path.parts):
            continue
        rel = str(py_path.relative_to(ws))
        index.nodes.append(CodeGraphNode(path=rel, kind="module"))
        try:
            tree = ast.parse(py_path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
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
