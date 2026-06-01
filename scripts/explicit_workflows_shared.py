"""Explicit imports for workflows/_shared.py and its consumers."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WF = REPO / "packages/nimbusware_console/pages/config_tooling/workflows"

SOURCES = {
    "_shared_catalog": WF / "_shared_catalog.py",
    "_shared_displays_a": WF / "_shared_displays_a.py",
    "_shared_displays_b": WF / "_shared_displays_b.py",
    "_shared_explainers": WF / "_shared_explainers.py",
    "_shared_integrator": WF / "_shared_integrator.py",
    "_shared_session": WF / "_shared_session.py",
}

STDLIB = {
    "Any",
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
    "Path",
    "os",
    "json",
    "csv",
    "io",
    "math",
    "datetime",
    "timezone",
    "urlencode",
    "st",
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
                if alias.name != "*":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
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


def _format_import(module: str, symbols: list[str]) -> str:
    symbols = sorted(symbols)
    if len(symbols) <= 4:
        return f"from {module} import {', '.join(symbols)}"
    joined = ",\n    ".join(symbols)
    return f"from {module} import (\n    {joined},\n)"


def _build_symbol_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, path in SOURCES.items():
        for name in _module_exports(path):
            mapping[name] = key
    return mapping


def write_shared_barrel() -> None:
    blocks = ["from __future__ import annotations", ""]
    for key in SOURCES:
        names = sorted(_module_exports(SOURCES[key]))
        mod = f"nimbusware_console.pages.config_tooling.workflows.{key}"
        joined = ",\n    ".join(names)
        blocks.append(f"from {mod} import (")
        blocks.append(f"    {joined},")
        blocks.append(")")
        blocks.append("")
    (WF / "_shared.py").write_text("\n".join(blocks), encoding="utf-8")
    print("wrote workflows/_shared.py")


def migrate_consumer(path: Path, symbol_map: dict[str, str]) -> bool:
    text = path.read_text(encoding="utf-8")
    star = "from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403\n"
    if star not in text:
        return False
    used = _used_names(path)
    # Shim files that only re-export have no local symbol usage — keep full barrel.
    body_without_star = text.replace(star, "")
    if not body_without_star.strip():
        blocks = ["from __future__ import annotations", ""]
        for key in SOURCES:
            names = sorted(_module_exports(SOURCES[key]))
            mod = f"nimbusware_console.pages.config_tooling.workflows.{key}"
            joined = ",\n    ".join(names)
            blocks.append(f"from {mod} import (")
            blocks.append(f"    {joined},")
            blocks.append(")")
            blocks.append("")
        path.write_text("\n".join(blocks), encoding="utf-8")
        return True
    by_source: dict[str, set[str]] = {}
    for name in used:
        if name in STDLIB:
            continue
        src = symbol_map.get(name)
        if src:
            by_source.setdefault(src, set()).add(name)
    import_lines: list[str] = []
    for key in SOURCES:
        symbols = by_source.get(key)
        if symbols:
            mod = f"nimbusware_console.pages.config_tooling.workflows.{key}"
            import_lines.append(_format_import(mod, list(symbols)))
    block = "\n".join(import_lines)
    path.write_text(text.replace(star, block + "\n"), encoding="utf-8")
    return True


def main() -> None:
    write_shared_barrel()
    symbol_map = _build_symbol_map()
    changed = 0
    paths = sorted(WF.rglob("*.py"))
    bundles_shared = REPO / "packages/nimbusware_console/pages/config_tooling/bundles/_shared.py"
    paths.append(bundles_shared)
    for path in paths:
        if path.name == "_shared.py" and path.parent == WF:
            continue
        if migrate_consumer(path, symbol_map):
            print(path.relative_to(REPO))
            changed += 1
    print(f"migrated {changed} consumers")


if __name__ == "__main__":
    main()
