from __future__ import annotations

import ast
from pathlib import Path

_COMMON = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "nimbusware_orchestrator"
    / "llm"
    / "common.py"
)

_REQUIRED = frozenset(
    {
        "LlmPlanResponse",
        "_finalize_critique_gate",
        "_parse_verdict",
    },
)


def _defined_or_imported(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
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


def test_llm_common_exports_core_symbols() -> None:
    names = _defined_or_imported(_COMMON)
    missing = sorted(_REQUIRED - names)
    assert not missing, f"common.py missing exports: {missing}"


def test_llm_critique_modules_use_explicit_common_imports() -> None:
    """Critique modules must import common symbols explicitly (no star imports)."""
    root = _COMMON.parent
    offenders: list[str] = []
    for path in sorted(root.glob("*_critique.py")):
        text = path.read_text(encoding="utf-8")
        if "from nimbusware_orchestrator.llm.common import *" in text:
            offenders.append(path.name)
    assert not offenders, "Critique modules must not star-import common:\n" + "\n".join(
        offenders,
    )
