#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "packages"

ALLOWED_PREFIXES = (
    "orchestrator.workflow.",
    "orchestrator._pipeline.",
    "orchestrator.campaign.",
    "orchestrator.slice.",
    "orchestrator.stack.",
    "orchestrator.integrator.",
    "orchestrator.completion_evaluator",
    "config.workflow_read",
    "config.resolved_config",
    "compute.mesh_stage_runner",
)

SCAN_ROOTS = (
    PACKAGES / "console",
    PACKAGES / "api",
    PACKAGES / "maker",
    PACKAGES / "projections",
)

FORBIDDEN_MODULES = (
    "orchestrator.workflow.blocks_simple",
    "orchestrator.workflow.campaign",
    "orchestrator.workflow.memory",
    "orchestrator.workflow.parallel_critics",
    "orchestrator.workflow.parallel_writers",
    "orchestrator.workflow.refactor",
    "orchestrator.workflow.research",
    "orchestrator.workflow.scan_critique",
    "orchestrator.workflow.universal_critique",
    "orchestrator.workflow.agent_evaluator",
)


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.py") if "__pycache__" not in path.parts and path.is_file()
    )


def _module_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            mods.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    return mods


def collect_violations() -> list[str]:
    violations: list[str] = []
    for scan_root in SCAN_ROOTS:
        if not scan_root.is_dir():
            continue
        for path in _iter_python_files(scan_root):
            rel = path.relative_to(PACKAGES.parent).as_posix()
            for mod in _module_imports(path):
                if not any(mod == forbidden or mod.startswith(f"{forbidden}.") for forbidden in FORBIDDEN_MODULES):
                    continue
                if any(rel.startswith(prefix.replace(".", "/") + "/") for prefix in ALLOWED_PREFIXES):
                    continue
                violations.append(f"{rel}: {mod}")
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print(
            "workflow registry gate: use orchestrator.workflow.registry loaders "
            "instead of direct workflow block imports in console/api/maker/projections:",
            file=sys.stderr,
        )
        for item in sorted(violations):
            print(f"  {item}", file=sys.stderr)
        return 1
    print("workflow registry gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
