#!/usr/bin/env python3

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCH = ROOT / "packages" / "orchestrator"

MOVES: tuple[tuple[str, str], ...] = (
    ("launch_eval_catalog.py", "launch/launch_eval_catalog.py"),
    ("launch_evaluator.py", "launch/launch_evaluator.py"),
    ("launch_flow_resolver.py", "launch/launch_flow_resolver.py"),
    ("launch_test_llm.py", "launch/launch_test_llm.py"),
    ("launch_test_stage.py", "launch/launch_test_stage.py"),
    ("escalation_execution.py", "escalation/escalation_execution.py"),
    ("escalation_policy_breadth.py", "escalation/escalation_policy_breadth.py"),
    ("escalation_threshold.py", "escalation/escalation_threshold.py"),
    ("gate_override_execution.py", "escalation/gate_override_execution.py"),
    ("improvement_council.py", "improvement/improvement_council.py"),
    ("improvement_council_backlog.py", "improvement/improvement_council_backlog.py"),
    ("improvement_scope.py", "improvement/improvement_scope.py"),
    ("resolution_council.py", "improvement/resolution_council.py"),
    ("diagnose_learn.py", "improvement/diagnose_learn.py"),
    ("feature_gap_matrix.py", "improvement/feature_gap_matrix.py"),
    ("interaction_surface_critic.py", "interaction/interaction_surface_critic.py"),
    ("interaction_surface_map.py", "interaction/interaction_surface_map.py"),
    ("js_framework_detect.py", "factory/js_framework_detect.py"),
    ("human_fidelity.py", "factory/human_fidelity.py"),
    ("self_refinement_policy.py", "workflow/self_refinement_policy.py"),
)

IMPORT_REPLACEMENTS: tuple[tuple[str, str], ...] = tuple(
    (
        f"from orchestrator.{src.replace('.py', '')} import",
        f"from orchestrator.{dest.rsplit('/', 1)[0].replace('/', '.')}.{Path(dest).stem} import",
    )
    for src, dest in MOVES
) + tuple(
    (
        f"import orchestrator.{src.replace('.py', '')}",
        f"import orchestrator.{dest.rsplit('/', 1)[0].replace('/', '.')}.{Path(dest).stem}",
    )
    for src, dest in MOVES
)


def main() -> None:
    for sub in ("launch", "escalation", "improvement", "interaction"):
        subdir = ORCH / sub
        subdir.mkdir(parents=True, exist_ok=True)
        init = subdir / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")

    for src_name, dest_rel in MOVES:
        src = ORCH / src_name
        dest = ORCH / dest_rel
        if not src.is_file():
            raise SystemExit(f"missing: {src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)

    skip_dirs = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache"}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".md", ".yaml", ".yml", ".ps1", ".sh"}:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        new = text
        for old, new_imp in IMPORT_REPLACEMENTS:
            new = new.replace(old, new_imp)
        if new != text:
            path.write_text(new, encoding="utf-8")

    subprocess.run(
        ["poetry", "run", "ruff", "check", "--fix", "packages/orchestrator"], check=False
    )


if __name__ == "__main__":
    main()
