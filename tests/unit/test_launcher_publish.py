from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_launcher_artifact_name_has_platform_suffix() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish" / "launcher_artifact_name.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    name = proc.stdout.strip()
    assert name.startswith("NimbuswareLauncher-")
    if sys.platform == "win32":
        assert name.endswith(".exe")
