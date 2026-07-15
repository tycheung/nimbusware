from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

_SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        ".tox",
        ".eggs",
    },
)


def should_skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.startswith(".")


def iter_workspace_files(workspace: Path, *, suffix: str | None = None) -> Iterator[Path]:
    """Yield files under workspace, pruning venv/cache/hidden directories."""
    root = workspace.resolve()
    for dirpath, dirnames, filenames in os.walk(str(root), topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for name in filenames:
            if suffix is not None and not name.endswith(suffix):
                continue
            yield Path(dirpath, name)
