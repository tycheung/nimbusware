"""Wrapper so ``pytest tests/e2e`` can invoke operator smoke (see ``scripts/e2e_smoke.py``)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "e2e_smoke.py"


def test_operator_e2e_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--profile", "app", "--skip-install-check"],
        cwd=REPO,
        check=False,
    )
    assert proc.returncode == 0, "scripts/e2e_smoke.py --profile app failed; run it for details"
