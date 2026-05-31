from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _shallow_mapping_field_diff(
    old: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    keys = sorted(set(old) | set(new))
    added = [k for k in keys if k not in old]
    removed = [k for k in keys if k not in new]
    changed: list[str] = []
    unchanged: list[str] = []
    for k in keys:
        if k in old and k in new:
            if old[k] != new[k]:
                changed.append(k)
            else:
                unchanged.append(k)
    entries: list[dict[str, Any]] = []
    for k in changed:
        entries.append({"field": k, "before": old[k], "after": new[k]})
    return {
        "added_keys": added,
        "removed_keys": removed,
        "changed_keys": changed,
        "unchanged_keys": unchanged,
        "changed_field_entries": entries,
    }


def full_workflow_merge_diff(
    before_disk: Mapping[str, Any] | None,
    merged_preview: Mapping[str, Any] | None,
    *,
    pasted_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if before_disk is None or merged_preview is None:
        return {"error": "before_disk and merged_preview are required"}
    if not isinstance(before_disk, dict) or not isinstance(merged_preview, dict):
        return {"error": "before_disk and merged_preview must be dict mappings"}
    b: dict[str, Any] = before_disk
    m: dict[str, Any] = merged_preview
    all_keys = sorted(set(b) | set(m))
    added_top = [k for k in all_keys if k not in b]
    removed_top = [k for k in all_keys if k not in m]
    changed_top: list[str] = []
    unchanged_top: list[str] = []
    for k in all_keys:
        if k in b and k in m:
            if b[k] != m[k]:
                changed_top.append(k)
            else:
                unchanged_top.append(k)
    out: dict[str, Any] = {
        "added_top_level_keys": added_top,
        "removed_top_level_keys": removed_top,
        "changed_top_level_keys": changed_top,
        "unchanged_top_level_keys": unchanged_top,
    }
    if isinstance(pasted_root, dict):
        disk_only = sorted(str(k) for k in b if k not in pasted_root)
        out["disk_only_top_level_keys"] = disk_only
        paste_only = sorted(str(k) for k in pasted_root if k not in b)
        out["paste_only_top_level_keys"] = paste_only
        out["pasted_top_level_keys"] = sorted(str(k) for k in pasted_root)
    subtrees: dict[str, Any] = {}
    for k in ("integrator_gate", "agent_evaluator"):
        if k in changed_top and isinstance(b.get(k), dict) and isinstance(m.get(k), dict):
            subtrees[k] = _shallow_mapping_field_diff(b[k], m[k])
    if subtrees:
        out["subtree_field_diffs"] = subtrees
    return out


_SUBTREE_CHANGED_KEYS_CAP = 12
_SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS = 6


