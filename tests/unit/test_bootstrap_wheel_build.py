from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "packages" / "bootstrap"


def test_bootstrap_wheel_builds() -> None:
    if shutil.which("pip") is None:
        return
    build = subprocess.run(
        [sys.executable, "-m", "pip", "install", "build", "-q"],
        capture_output=True,
        check=False,
    )
    if build.returncode != 0:
        return
    dist = _PKG / "dist"
    if dist.is_dir():
        shutil.rmtree(dist, ignore_errors=True)
    proc = subprocess.run(
        [sys.executable, "-m", "build", str(_PKG)],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    wheels = list(dist.glob("*.whl"))
    assert wheels, "expected wheel in dist/"
