"""CLI tests for ``scripts/build_bundle_faiss_index.py`` (PLAN_GAP §14 #12, fo128)."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_bundle_faiss_index_help_lists_paths() -> None:
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "build_bundle_faiss_index.py"),
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
