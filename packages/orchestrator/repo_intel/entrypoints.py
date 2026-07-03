from __future__ import annotations

import re
from pathlib import Path


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

    for py in sorted(ws.rglob("__main__.py")):
        if any(part.startswith(".") for part in py.parts):
            continue
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

    for py in sorted(ws.rglob("app.py")):
        if any(part.startswith(".") for part in py.parts):
            continue
        rel = str(py.relative_to(ws)).replace("\\", "/")
        if "api" in rel or rel.endswith("app.py"):
            _add(rel)

    return entries


def discover_test_seed_modules(workspace: Path) -> set[str]:
    seeds: set[str] = set()
    ws = workspace.resolve()
    for conftest in sorted(ws.rglob("conftest.py")):
        if any(part.startswith(".") for part in conftest.parts):
            continue
        seeds.add(str(conftest.relative_to(ws)).replace("\\", "/"))
        for py in conftest.parent.glob("test_*.py"):
            seeds.add(str(py.relative_to(ws)).replace("\\", "/"))
    return seeds
