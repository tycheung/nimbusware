from __future__ import annotations

import difflib
from pathlib import Path


def unified_diff_from_edits(workspace: Path, edits: list[dict[str, str]]) -> str:
    chunks: list[str] = []
    for raw in edits:
        if not isinstance(raw, dict):
            continue
        rel = str(raw.get("path", "")).replace("\\", "/").lstrip("/")
        if not rel:
            continue
        fp = workspace / rel
        try:
            old = fp.read_text(encoding="utf-8") if fp.is_file() else ""
        except OSError:
            old = ""
        new = str(raw.get("content", ""))
        if old == new:
            continue
        diff_lines = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
        )
        chunk = "".join(diff_lines)
        if chunk:
            chunks.append(chunk)
    return "\n".join(chunks)


def preview_note_for_scoped_mode(plan_paths: tuple[str, ...] | list[str]) -> str:
    paths = ", ".join(plan_paths[:6])
    suffix = "…" if len(plan_paths) > 6 else ""
    return (
        f"Scoped implement will run ruff format and check --fix on: {paths}{suffix}\n"
        "(No file content changes until you click Apply.)"
    )
