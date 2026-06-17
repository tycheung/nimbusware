from __future__ import annotations

import subprocess
from pathlib import Path

from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_build_bundle_faiss_index_help_lists_paths() -> None:
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "faiss" / "build_bundle_faiss_index.py"),
            "--help",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--repo-root" in proc.stdout
    assert "--catalog" in proc.stdout
    assert "--out-dir" in proc.stdout
