from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "bootstrap_consumer.py"


def test_bootstrap_consumer_print_only() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--print-only"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "curl -fsSL" in proc.stdout
    assert "install_nimbusware.py" in proc.stdout
