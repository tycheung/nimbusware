from __future__ import annotations

import shutil
from pathlib import Path

FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "repos"


def fixture_repo_root(name: str) -> Path:
    root = FIXTURES_ROOT / name
    if not root.is_dir():
        raise FileNotFoundError(f"fixture repo missing: {root}")
    return root


def copy_fixture_repo(name: str, dest: Path) -> Path:
    src = fixture_repo_root(name)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest.resolve()
