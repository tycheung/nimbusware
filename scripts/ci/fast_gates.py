#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run_step(name: str, cmd: list[str]) -> int:
    print(f"=== {name} ===", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main() -> int:
    steps: list[tuple[str, list[str]]] = [
        ("ruff check", ["poetry", "run", "ruff", "check", "packages", "tests"]),
        (
            "workflow yaml gate",
            [sys.executable, str(ROOT / "scripts" / "ci" / "run_workflow_yaml_ci_gate.py")],
        ),
        (
            "loc budget gate",
            [sys.executable, str(ROOT / "scripts" / "ci" / "run_loc_budget_ci_gate.py")],
        ),
        (
            "package module size",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit/test_package_module_size.py",
                "-q",
            ],
        ),
        (
            "import boundary check",
            [sys.executable, str(ROOT / "scripts" / "ci" / "import_boundary_check.py")],
        ),
    ]

    failures: list[str] = []
    for name, cmd in steps:
        if _run_step(name, cmd) != 0:
            failures.append(name)

    if failures:
        print(f"fast gates failed: {', '.join(failures)}", file=sys.stderr)
        return 1

    print("fast gates: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
