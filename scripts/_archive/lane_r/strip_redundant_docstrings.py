"""Remove module and function docstrings while preserving source layout."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _docstring_line_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        value = first.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            end = getattr(first, "end_lineno", first.lineno)
            ranges.append((first.lineno, end))
    return ranges


def strip_docstrings(source: str) -> str:
    tree = ast.parse(source)
    ranges = sorted(_docstring_line_ranges(tree), reverse=True)
    lines = source.splitlines(keepends=True)
    for start, end in ranges:
        del lines[start - 1 : end]
        if start - 1 < len(lines) and lines[start - 1].strip() == "":
            del lines[start - 1]
    return "".join(lines)


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parents[1]
    default_paths = [
        root / "packages/nimbusware_console/bundle_catalog/catalog_local",
        root / "packages/nimbusware_console/components/explainer_panel.py",
        root / "packages/nimbusware_client/http.py",
        root / "packages/nimbusware_console/pages/config_tooling/workflows/integrator",
        root / "packages/nimbusware_console/pages/config_tooling/bundles/faiss_readiness",
        root / "packages/nimbusware_console/enterprise_console.py",
        root / "packages/nimbusware_console/enterprise_console_ui.py",
        root / "tests/unit/test_explainer_panel.py",
        root / "tests/unit/test_nimbusware_client.py",
    ]
    paths = [Path(p) for p in argv[1:]] if len(argv) > 1 else default_paths
    changed = 0
    for path in paths:
        files = sorted(path.rglob("*.py")) if path.is_dir() else [path]
        for file in files:
            if not file.is_file():
                continue
            original = file.read_text(encoding="utf-8")
            updated = strip_docstrings(original)
            if updated != original:
                file.write_text(updated, encoding="utf-8", newline="\n")
                changed += 1
                try:
                    print(file.relative_to(root))
                except ValueError:
                    print(file)
    print(f"updated {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
