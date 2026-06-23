#!/usr/bin/env python3
"""CI gate: workflow explainer __init__.py blocks must match registry (C50)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYNC = ROOT / "scripts" / "codegen" / "sync_workflow_explainer_init.py"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(SYNC), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        print(
            "workflow explainer init gate failed — run: "
            "poetry run python scripts/codegen/sync_workflow_explainer_init.py",
            file=sys.stderr,
        )
        return 1
    print("workflow explainer init gate: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
