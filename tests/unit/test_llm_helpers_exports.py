from __future__ import annotations

import ast
from pathlib import Path

_GATE = (
    Path(__file__).resolve().parents[2]
    / "packages"
    / "orchestrator"
    / "llm"
    / "gate_helpers.py"
)

_REQUIRED = frozenset(
    {
        "LlmPlanResponse",
        "_finalize_critique_gate",
        "_parse_verdict",
        "execute_plan_stage_llm",
        "execute_agent_evaluator_policy_llm",
        "emit_stub_plan_stage",
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


def test_llm_gate_helpers_exports_core_symbols() -> None:
    """sak522: plan/agent_evaluator live in gate_helpers after inventory delete."""
    names = _defined_or_imported(_GATE)
    missing = sorted(_REQUIRED - names)
    assert not missing, f"gate_helpers.py missing exports: {missing}"


def test_llm_critique_modules_use_explicit_common_imports() -> None:
    """Critique modules must import symbols explicitly (no star imports)."""
    root = _GATE.parent
    offenders: list[str] = []
    for path in sorted(root.glob("*_critique.py")):
        text = path.read_text(encoding="utf-8")
        if "from orchestrator.llm.chat_facade import *" in text:
            offenders.append(path.name)
        if "from orchestrator.llm.gate_helpers import *" in text:
            offenders.append(path.name)
    assert not offenders, "Critique modules must not star-import helpers:\n" + "\n".join(
        offenders,
    )
