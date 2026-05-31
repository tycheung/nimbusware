from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.integrator_preview.merge.diff import (
    _SUBTREE_CHANGED_KEYS_CAP,
)


def full_workflow_merge_attention_rows(diff: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return []
    rows: list[dict[str, str]] = []
    removed = diff.get("removed_top_level_keys")
    if isinstance(removed, list) and removed:
        rows.append(
            {
                "flag": "Removed top-level keys (paste omits these; they disappear on apply)",
                "keys": ", ".join(str(x) for x in removed),
            },
        )
    added = diff.get("added_top_level_keys")
    if isinstance(added, list) and added:
        rows.append(
            {
                "flag": "Added top-level keys (paste introduces new YAML sections on disk)",
                "keys": ", ".join(str(x) for x in sorted(added)),
            },
        )
    disk_only = diff.get("disk_only_top_level_keys")
    if isinstance(disk_only, list) and disk_only:
        rows.append(
            {
                "flag": (
                    "Disk-only top-level keys (not in pasted YAML; unchanged on disk after "
                    "shallow merge)"
                ),
                "keys": ", ".join(str(x) for x in disk_only),
            },
        )
    paste_only = diff.get("paste_only_top_level_keys")
    if isinstance(paste_only, list) and paste_only:
        rows.append(
            {
                "flag": (
                    "Paste-only top-level keys (in pasted YAML but not on disk; new sections "
                    "after shallow merge)"
                ),
                "keys": ", ".join(str(x) for x in paste_only),
            },
        )
    pasted_keys = diff.get("pasted_top_level_keys")
    if isinstance(pasted_keys, list) and pasted_keys:
        rows.append(
            {
                "flag": (
                    "Pasted top-level keys (YAML root keys in this paste; compare with "
                    "disk-only / added / removed hints above)"
                ),
                "keys": ", ".join(str(x) for x in pasted_keys),
            },
        )
    changed = diff.get("changed_top_level_keys")
    if (
        isinstance(changed, list)
        and "integrator_gate" in changed
        and "agent_evaluator" in changed
    ):
        rows.append(
            {
                "flag": "Both integrator_gate and agent_evaluator change in one paste",
                "keys": "Review subtree field tables and raw JSON before apply.",
            },
        )
    subtrees = diff.get("subtree_field_diffs")
    if isinstance(subtrees, dict):
        removed_parts: list[str] = []
        added_parts: list[str] = []
        changed_parts: list[str] = []
        for name in ("integrator_gate", "agent_evaluator"):
            inner = subtrees.get(name)
            if not isinstance(inner, dict):
                continue
            removed = inner.get("removed_keys")
            if isinstance(removed, list) and removed:
                removed_parts.append(
                    f"{name}: removed {', '.join(str(x) for x in removed)}",
                )
            added_inner = inner.get("added_keys")
            if isinstance(added_inner, list) and added_inner:
                added_parts.append(
                    f"{name}: added {', '.join(str(x) for x in added_inner)}",
                )
            changed_inner = inner.get("changed_keys")
            if isinstance(changed_inner, list) and changed_inner:
                visible = [str(x) for x in changed_inner[:_SUBTREE_CHANGED_KEYS_CAP]]
                overflow = len(changed_inner) - len(visible)
                tail = f" (+{overflow} more)" if overflow > 0 else ""
                changed_parts.append(
                    f"{name}: changed {', '.join(visible)}{tail}",
                )
        if removed_parts:
            rows.append(
                {
                    "flag": (
                        "Removed shallow keys under integrator_gate / agent_evaluator "
                        "(paste drops those YAML fields on apply)"
                    ),
                    "keys": "; ".join(removed_parts),
                },
            )
        if added_parts:
            rows.append(
                {
                    "flag": (
                        "Added shallow keys under integrator_gate / agent_evaluator "
                        "(paste introduces new YAML fields under those subtrees on apply)"
                    ),
                    "keys": "; ".join(added_parts),
                },
            )
        if changed_parts:
            rows.append(
                {
                    "flag": (
                        "Changed shallow keys under integrator_gate / agent_evaluator "
                        "(paste alters existing YAML values under those subtrees on apply)"
                    ),
                    "keys": "; ".join(changed_parts),
                },
            )
    return rows


