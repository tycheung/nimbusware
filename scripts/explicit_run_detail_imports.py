"""Replace run_detail star imports with explicit symbol imports."""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "packages/nimbusware_console/pages/run_detail"

SOURCES = {
    "_imports_common": PKG / "_imports_common.py",
    "_imports_display_a": PKG / "_imports_display_a.py",
    "_imports_display_b": PKG / "_imports_display_b.py",
    "_imports_tail": PKG / "_imports.py",
}

CONSUMERS = [
    p
    for p in PKG.glob("*.py")
    if p.name not in {"__init__.py", "_imports.py", "_imports_common.py", "_imports_display_a.py", "_imports_display_b.py"}
]

STDLIB = {
    "Any",
    "Optional",
    "True",
    "False",
    "None",
    "dict",
    "list",
    "str",
    "int",
    "float",
    "bool",
    "tuple",
    "set",
    "bytes",
    "len",
    "isinstance",
    "range",
    "enumerate",
    "zip",
    "min",
    "max",
    "sorted",
    "print",
    "Exception",
}


def _module_exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
    return names


def _used_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
    return used


def _build_symbol_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for source, path in SOURCES.items():
        for name in _module_exports(path):
            mapping[name] = source
    return mapping


def _format_import(source: str, symbols: list[str]) -> str:
    symbols = sorted(symbols)
    if len(symbols) <= 4:
        inner = ", ".join(symbols)
        return f"from nimbusware_console.pages.run_detail.{source} import {inner}"
    lines = ",\n    ".join(symbols)
    return f"from nimbusware_console.pages.run_detail.{source} import (\n    {lines},\n)"


def migrate(path: Path, symbol_map: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8")
    if "from nimbusware_console.pages.run_detail._imports import *" not in text:
        return False

    used = _used_names(path)
    by_source: dict[str, set[str]] = {}
    for name in used:
        if name in STDLIB or name.startswith("_") and name not in symbol_map:
            continue
        source = symbol_map.get(name)
        if source:
            by_source.setdefault(source, set()).add(name)

    import_lines: list[str] = []
    for source in ("_imports_common", "_imports_display_a", "_imports_display_b", "_imports_tail"):
        symbols = by_source.get(source)
        if symbols:
            import_lines.append(_format_import(source, list(symbols)))

    block = "\n".join(import_lines)
    text = text.replace(
        "from nimbusware_console.pages.run_detail._imports import *  # noqa: F403\n",
        block + "\n",
    )
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    symbol_map = _build_symbol_map()
    changed = 0
    for path in CONSUMERS:
        if migrate(path, symbol_map):
            print(path.name)
            changed += 1
    print(f"updated {changed} modules")


if __name__ == "__main__":
    main()
