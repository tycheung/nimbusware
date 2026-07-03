from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.interaction.interaction_surface_map import InteractionSurfaceMap


def ism_snapshot_path(workspace: Path, slice_id: str) -> Path:
    safe = slice_id.replace("/", "_") or "slice"
    return workspace.resolve() / ".nimbusware" / "ism" / f"{safe}.json"


def persist_ism_snapshot(workspace: Path, slice_id: str, ism: InteractionSurfaceMap) -> Path:
    path = ism_snapshot_path(workspace, slice_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ism.to_dict(), indent=2), encoding="utf-8")
    return path


def load_ism_snapshot(path: Path) -> InteractionSurfaceMap | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return InteractionSurfaceMap.from_dict(data)


def _surface_paths(ism: InteractionSurfaceMap) -> set[str]:
    return {s.path for s in ism.surfaces}


def diff_ism_snapshots(
    before: InteractionSurfaceMap | None,
    after: InteractionSurfaceMap,
) -> dict[str, Any]:
    before_paths = _surface_paths(before) if before else set()
    after_paths = _surface_paths(after)
    added = sorted(after_paths - before_paths)
    removed = sorted(before_paths - after_paths)
    changed: list[str] = []
    if before:
        overlap = before_paths & after_paths
        before_by = {s.path: s for s in before.surfaces if s.path in overlap}
        after_by = {s.path: s for s in after.surfaces if s.path in overlap}
        for path in sorted(overlap):
            if before_by[path].kind != after_by[path].kind:
                changed.append(path)
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "before_count": len(before_paths),
        "after_count": len(after_paths),
    }
