from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "e2e_smoke.py"


def test_operator_e2e_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--profile", "app", "--skip-install-check"],
        cwd=REPO,
        check=False,
    )
    assert proc.returncode == 0, "scripts/e2e_smoke.py --profile app failed; run it for details"
