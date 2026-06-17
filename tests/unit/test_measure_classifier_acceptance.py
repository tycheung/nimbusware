from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def test_measure_classifier_acceptance_meets_target() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "benchmarks" / "measure_classifier_acceptance.py"),
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
