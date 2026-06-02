from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_build_bundle_faiss_index_help_lists_flags() -> None:
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
    assert "--catalog" in proc.stdout
    assert "--out-dir" in proc.stdout
    assert "--repo-root" in proc.stdout


@pytest.mark.skipif(
    importlib.util.find_spec("faiss") is None,
    reason="optional faiss group not installed",
)
def test_build_bundle_faiss_index_custom_catalog_and_out(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(
        "version: 1\n"
        "workflow_bundle_map:\n"
        "  default: b1\n"
        "bundles:\n"
        "  - id: b1\n"
        "    title: One\n"
        "    tags: [a]\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "idx"
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "build_bundle_faiss_index.py"),
            "--catalog",
            str(catalog),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert (out_dir / "faiss.index").is_file()
    assert (out_dir / "bundle_order.json").is_file()
