from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from env.env_flags import nimbusware_workspace_snapshot_dir


def snapshot_root() -> Path:
    raw = nimbusware_workspace_snapshot_dir()
    if raw:
        return Path(raw).resolve()
    return Path(".cache/nimbusware_workspace_snapshots").resolve()


def create_workspace_snapshot(
    workspace: Path,
    *,
    run_id: str,
    label: str,
    paths: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    ws = workspace.resolve()
    dest = snapshot_root() / run_id / label
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for raw in paths:
        rel = str(raw).replace("\\", "/").lstrip("/")
        if not rel or ".." in rel.split("/"):
            continue
        src = ws / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)
    snapshot_id = f"{run_id}:{label}"
    return {
        "snapshot_id": snapshot_id,
        "root": str(dest),
        "paths": copied,
        "workspace": str(ws),
    }


def restore_workspace_snapshot(workspace: Path, snapshot: dict[str, Any]) -> list[str]:
    ws = workspace.resolve()
    root = Path(str(snapshot.get("root") or "")).resolve()
    restored: list[str] = []
    paths = snapshot.get("paths")
    if not isinstance(paths, list):
        return restored
    for rel in paths:
        rel_s = str(rel).replace("\\", "/").lstrip("/")
        src = root / rel_s
        if not src.is_file():
            continue
        target = ws / rel_s
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        restored.append(rel_s)
    return restored
