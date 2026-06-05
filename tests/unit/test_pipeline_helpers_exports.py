"""Pipeline _helpers must export symbols mixins rely on (Phase 4 guard)."""

from __future__ import annotations

import ast
from pathlib import Path

_HELPERS = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "nimbusware_orchestrator"
    / "_pipeline"
    / "_helpers.py"
)

_REQUIRED = frozenset(
    {
        "InMemoryEventStore",
        "EventType",
        "validate_event_dict",
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


def test_pipeline_helpers_exports_core_symbols() -> None:
    names = _defined_or_imported(_HELPERS)
    missing = sorted(_REQUIRED - names)
    assert not missing, f"_helpers.py missing exports: {missing}"


def test_pipeline_mixins_use_explicit_helpers_imports() -> None:
    """Mixins must import _helpers symbols explicitly (no star imports)."""
    root = _HELPERS.parent
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        if path.name in {
            "__init__.py",
            "_helpers.py",
            "compose.py",
            "dev_factory.py",
            "critique_gates.py",
            "optional_stages.py",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        if "from nimbusware_orchestrator._pipeline._helpers import *" in text:
            offenders.append(path.name)
    assert not offenders, "Mixins must not star-import _helpers:\n" + "\n".join(offenders)
