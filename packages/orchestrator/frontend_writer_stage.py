from __future__ import annotations

from pathlib import Path
from typing import Literal

from env import find_repo_root

_FRONTEND_SUFFIXES = (".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte")
_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".nimbusware"})

_MINIMAL_INDEX_PATH = (
    find_repo_root() / "configs" / "factory" / "frontend_minimal_index.html"
)


def _minimal_index_html() -> str:
    return _MINIMAL_INDEX_PATH.read_text(encoding="utf-8")


def discover_frontend_files(workspace: Path) -> list[Path]:
    ws = workspace.resolve()
    found: list[Path] = []
    for path in ws.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(ws).parts
        if any(part in _SKIP_DIRS for part in rel_parts):
            continue
        if path.suffix.lower() in _FRONTEND_SUFFIXES:
            found.append(path)
    return sorted(found)


def run_frontend_writer_stage(workspace: Path) -> tuple[int, str, Literal["validate", "scaffold"]]:
    """Ensure workspace has web assets: validate existing files or scaffold minimal HTML."""
    ws = workspace.resolve()
    existing = discover_frontend_files(ws)
    if existing:
        rel = ", ".join(str(p.relative_to(ws)).replace("\\", "/") for p in existing[:5])
        suffix = f" (+{len(existing) - 5} more)" if len(existing) > 5 else ""
        return 0, f"frontend_writer validated {len(existing)} file(s): {rel}{suffix}", "validate"

    target = ws / "static" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        target.write_text(_minimal_index_html(), encoding="utf-8")
    rel = str(target.relative_to(ws)).replace("\\", "/")
    return 0, f"frontend_writer scaffolded {rel}", "scaffold"
