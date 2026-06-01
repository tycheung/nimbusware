"""Replace llm critique star imports with explicit common imports."""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LLM = REPO / "packages/hermes_orchestrator/llm"
COMMON = LLM / "common.py"

STAR = "from hermes_orchestrator.llm.common import *  # noqa: F403\n"

SKIP = {
    "__init__.py",
    "common.py",
    "plan_stage.py",
    "agent_evaluator.py",
}


def _common_exports() -> set[str]:
    tree = ast.parse(COMMON.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _local_import_names(path: Path) -> set[str]:
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
        return f"from hermes_orchestrator.llm.common import {', '.join(symbols)}"
    joined = ",\n    ".join(symbols)
    return f"from hermes_orchestrator.llm.common import (\n    {joined},\n)"


def explicitize(path: Path, exports: set[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    if STAR not in text:
        return False
    used = _used_names(path) - _local_import_names(path)
    needed = sorted(used & exports)
    if not needed:
        return False
    text = text.replace(STAR, _format_import(needed) + "\n")
    path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    exports = _common_exports()
    changed = 0
    for path in sorted(LLM.glob("*.py")):
        if path.name in SKIP:
            continue
        if explicitize(path, exports):
            print(path.name)
            changed += 1
    print(f"updated {changed} critique modules")


if __name__ == "__main__":
    main()
