"""Replace pipeline mixin star imports with explicit _helpers imports."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PIPELINE = REPO / "packages/nimbusware_orchestrator/_pipeline"
HELPERS = PIPELINE / "_helpers.py"

STAR = "from nimbusware_orchestrator._pipeline._helpers import *  # noqa: F403\n"

SKIP = {
    "__init__.py",
    "_helpers.py",
    "compose.py",
    "dev_factory.py",
    "critique_gates.py",
    "optional_stages.py",
}


def _helpers_exports() -> set[str]:
    tree = ast.parse(HELPERS.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _used_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "self":
                continue
    return used


def _format_import(symbols: list[str]) -> str:
    symbols = sorted(symbols)
    if len(symbols) <= 5:
        return f"from nimbusware_orchestrator._pipeline._helpers import {', '.join(symbols)}"
    joined = ",\n    ".join(symbols)
    return f"from nimbusware_orchestrator._pipeline._helpers import (\n    {joined},\n)"


def explicitize(path: Path, exports: set[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    if STAR not in text:
        return False
    used = _used_names(path)
    needed = sorted(used & exports)
    if not needed:
        return False
    text = text.replace(STAR, _format_import(needed) + "\n\n")
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    exports = _helpers_exports()
    changed = 0
    for path in sorted(PIPELINE.glob("*.py")):
        if path.name in SKIP:
            continue
        if explicitize(path, exports):
            print(path.name)
            changed += 1
    print(f"updated {changed} mixin modules")


if __name__ == "__main__":
    main()
