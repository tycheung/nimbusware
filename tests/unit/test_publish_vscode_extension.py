from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "publish" / "publish_vscode_extension.py"
_EXT = _REPO / "extensions" / "nimbusware-status"


def test_publish_vscode_extension_help_lists_publish_flag() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "--publish" in proc.stdout


def test_publish_vscode_extension_package_only() -> None:
    if shutil.which("npm.cmd") is None and shutil.which("npm") is None:
        return
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--skip-gate"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "VSIX packaged:" in proc.stdout
    assert list(_EXT.glob("*.vsix")), "expected .vsix in extensions/nimbusware-status/"
