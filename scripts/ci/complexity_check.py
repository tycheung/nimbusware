#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = ROOT / "packages" / "orchestrator" / "_pipeline"
BRANCH_THRESHOLD = 25


class _BranchCounter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.count = 0

    def visit_If(self, node: ast.If) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.count += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        if isinstance(node.op, (ast.And, ast.Or)):
            self.count += max(len(node.values) - 1, 0)
        self.generic_visit(node)


def branch_count(node: ast.AST) -> int:
    counter = _BranchCounter()
    counter.visit(node)
    return counter.count


def _function_nodes(tree: ast.Module) -> list[tuple[str, ast.AST]]:
    found: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append((node.name, node))
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qual = f"{node.name}.{item.name}"
                    found.append((qual, item))
    return found


def collect_high_branch_functions(
    *,
    pipeline_dir: Path | None = None,
    threshold: int = BRANCH_THRESHOLD,
) -> list[tuple[str, str, int]]:
    """Return (relative_path, function_name, branch_count) for functions over threshold."""
    pipeline_dir = pipeline_dir or PIPELINE_DIR
    flagged: list[tuple[str, str, int]] = []
    for path in sorted(pipeline_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(pipeline_dir.parent.parent).as_posix()
        for name, fn in _function_nodes(tree):
            count = branch_count(fn)
            if count > threshold:
                flagged.append((rel, name, count))
    return flagged


def main() -> int:
    flagged = collect_high_branch_functions()
    if flagged:
        print(
            f"complexity check: {len(flagged)} function(s) exceed "
            f"{BRANCH_THRESHOLD} branches (warn only):",
            file=sys.stderr,
        )
        for rel, name, count in flagged:
            print(f"  {rel}:{name} — {count} branches", file=sys.stderr)
    else:
        print(f"complexity check: ok (no functions > {BRANCH_THRESHOLD} branches)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
