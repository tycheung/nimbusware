#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOT_PATHS = (
    ROOT / "packages" / "orchestrator" / "_pipeline",
    ROOT / "packages" / "config" / "resolved_config.py",
    ROOT / "packages" / "orchestrator" / "workflow" / "registry.py",
)
MAX_NESTING = 6
MAX_BRANCHES = 18


class _ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.depth = 0
        self.max_depth = 0
        self.branches = 0

    def _visit_nested(self, node: ast.AST) -> None:
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)
        self.generic_visit(node)
        self.depth -= 1

    def visit_If(self, node: ast.If) -> None:
        self.branches += 1
        self._visit_nested(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_nested(node)

    def visit_While(self, node: ast.While) -> None:
        self._visit_nested(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.branches += len(node.handlers)
        self._visit_nested(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_nested(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.branches += len(node.cases)
        self._visit_nested(node)


def _iter_python_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts and path.is_file()
    )


def collect_violations() -> list[str]:
    violations: list[str] = []
    for hot in HOT_PATHS:
        for path in _iter_python_files(hot):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visitor = _ComplexityVisitor()
                    visitor.visit(node)
                    rel = path.relative_to(ROOT).as_posix()
                    if visitor.max_depth > MAX_NESTING:
                        violations.append(
                            f"{rel}:{node.name} nesting={visitor.max_depth} (max {MAX_NESTING})"
                        )
                    if visitor.branches > MAX_BRANCHES:
                        violations.append(
                            f"{rel}:{node.name} branches={visitor.branches} (max {MAX_BRANCHES})"
                        )
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("complexity gate violations:", file=sys.stderr)
        for item in sorted(violations):
            print(f"  {item}", file=sys.stderr)
        return 1
    print("complexity gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
