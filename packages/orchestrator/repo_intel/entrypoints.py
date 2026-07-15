from __future__ import annotations

import re
from pathlib import Path

from orchestrator.slice.repo_map import _should_skip_dir


def _iter_named_files(workspace: Path, filename: str) -> list[Path]:
    """Find ``filename`` under workspace, pruning venv/cache/hidden dirs."""
    root = workspace.resolve()
    root_s = str(root)
    found: list[Path] = []
    import os

    for dirpath, dirnames, filenames in os.walk(root_s, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        if filename in filenames:
            found.append(Path(dirpath, filename))
    return sorted(found)


def discover_entrypoint_modules(workspace: Path) -> list[str]:
    ws = workspace.resolve()
    entries: list[str] = []
    seen: set[str] = set()

    def _add(rel: str) -> None:
        key = rel.replace("\\", "/")
        if key not in seen:
            seen.add(key)
            entries.append(key)

    for rel in ("main.py", "app.py"):
        if (ws / rel).is_file():
            _add(rel)

    for py in _iter_named_files(ws, "__main__.py"):
        _add(str(py.relative_to(ws)).replace("\\", "/"))

    pyproject = ws / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            text = ""
        in_scripts = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[tool.poetry.scripts]"):
                in_scripts = True
                continue
            if in_scripts:
                if stripped.startswith("[") and not stripped.startswith("[tool.poetry.scripts"):
                    break
                match = re.match(r'^\s*[\w.-]+\s*=\s*["\']([^"\']+)["\']', line)
                if match:
                    target = match.group(1).split(":")[0].replace(".", "/")
                    for candidate in (f"{target}.py", f"{target}/__init__.py"):
                        if (ws / candidate).is_file():
                            _add(candidate)
                            break

    for py in _iter_named_files(ws, "app.py"):
        rel = str(py.relative_to(ws)).replace("\\", "/")
        if "api" in rel or rel.endswith("app.py"):
            _add(rel)

    return entries


def discover_test_seed_modules(workspace: Path) -> set[str]:
    seeds: set[str] = set()
    ws = workspace.resolve()
    for conftest in _iter_named_files(ws, "conftest.py"):
        seeds.add(str(conftest.relative_to(ws)).replace("\\", "/"))
        for py in conftest.parent.glob("test_*.py"):
            seeds.add(str(py.relative_to(ws)).replace("\\", "/"))
    return seeds
