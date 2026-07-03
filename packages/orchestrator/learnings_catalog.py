from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.improvement.diagnose_learn import learnings_dir


def list_workspace_learnings(workspace: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    directory = learnings_dir(workspace)
    if not directory.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if len(entries) >= limit:
            break
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        title = path.stem
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        entries.append(
            {
                "learning_id": path.stem,
                "path": str(path),
                "title": title,
                "excerpt": text[:500],
            },
        )
    return entries
