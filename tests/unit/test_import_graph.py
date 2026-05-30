"""Import graph — extensions must not import orchestrator at module level."""

from __future__ import annotations

import ast
from pathlib import Path


def _module_level_orchestrator_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("hermes_orchestrator"):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.startswith("hermes_orchestrator"):
                hits.append(mod)
    return hits


def test_extensions_has_no_module_level_orchestrator_imports() -> None:
    root = Path(__file__).resolve().parents[2] / "packages" / "hermes_extensions"
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        hits = _module_level_orchestrator_imports(path)
        if hits:
            offenders.append(f"{path.name}: {hits}")
    assert not offenders, "\n".join(offenders)
