from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "publish_bootstrap_release.py"


def test_publish_bootstrap_release_help_lists_upload_flags() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "--testpypi" in proc.stdout
    assert "--pypi" in proc.stdout


def test_publish_bootstrap_release_build_only() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--skip-gate"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "build + twine check OK" in proc.stdout
    assert (_REPO / "packages" / "nimbusware_bootstrap" / "dist").is_dir()
