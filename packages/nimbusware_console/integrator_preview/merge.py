from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    FIELD_VALUE_COLUMNS,
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    sequence_export_json,
    table_rows_csv,
)
import csv
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from hermes_extensions.personas import ALLOWED_SHELVES
from hermes_extensions.phase2 import ModuleIntegrator
from hermes_orchestrator.integrator_gate import (
    integrator_gate_workflow_enabled,
    load_bundle_tags_for_bundle_id,
    load_integrator_gate_emit_enabled,
    parse_integrator_gate_min_score_to_pass,
    parse_integrator_gate_project_tags,
)

from nimbusware_console.integrator_preview.parse import (
    ALLOWED_FULL_WORKFLOW_ROOT_KEYS,
    _FULL_WORKFLOW_MAPPING_KEYS,
)
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


def full_workflow_merge_overview_caption(diff: Mapping[str, Any] | None) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    added = _count("added_top_level_keys")
    removed = _count("removed_top_level_keys")
    changed = _count("changed_top_level_keys")
    unchanged = _count("unchanged_top_level_keys")
    return f"Top-level: +{added} / -{removed} / ~{changed} / ={unchanged}"


def full_workflow_merge_top_level_churn_count_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    n = (
        _count("added_top_level_keys")
        + _count("removed_top_level_keys")
        + _count("changed_top_level_keys")
    )
    return (
        "Dry-run top-level churn: **"
        f"{n}"
        "** key(s) added, removed, or value-changed (unchanged keys excluded)."
    )


def full_workflow_merge_diff_audit_fingerprint_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    try:
        payload = json.dumps(diff, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return None
    raw = payload.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return (
        "Dry-run merge diff fingerprint: SHA-256 prefix "
        f"``{digest}`` over **{len(raw)}** UTF-8 bytes (canonical JSON)."
    )


def full_workflow_merge_unchanged_with_churn_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    churn = (
        _count("added_top_level_keys")
        + _count("removed_top_level_keys")
        + _count("changed_top_level_keys")
    )
    if churn <= 0:
        return None
    raw_u = diff.get("unchanged_top_level_keys")
    if not isinstance(raw_u, list) or not raw_u:
        return None
    return (
        f"While **{churn}** top-level key(s) add/remove/change, **{len(raw_u)}** root "
        "key(s) remain **unchanged** in this shallow merge preview."
    )


def full_workflow_merge_removed_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("removed_top_level_keys")
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            cleaned.add(trimmed)
    if not cleaned:
        return None
    return "Removed top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_disk_only_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("disk_only_top_level_keys")
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            cleaned.add(trimmed)
    if not cleaned:
        return None
    return "Disk-only top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_paste_only_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("paste_only_top_level_keys")
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            cleaned.add(trimmed)
    if not cleaned:
        return None
    return "Paste-only top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_pasted_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("pasted_top_level_keys")
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            cleaned.add(trimmed)
    if not cleaned:
        return None
    return "Pasted top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_added_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("added_top_level_keys")
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            cleaned.add(trimmed)
    if not cleaned:
        return None
    return "Added top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_changed_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    raw = diff.get("changed_top_level_keys")
    if not isinstance(raw, list) or not raw:
        return None
    cleaned: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str):
            continue
        trimmed = entry.strip()
        if trimmed:
            cleaned.add(trimmed)
    if not cleaned:
        return None
    return "Changed top-level keys: " + ", ".join(sorted(cleaned)) + "."


def full_workflow_merge_unchanged_top_level_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None

    def _count(key: str) -> int:
        raw = diff.get(key)
        return len(raw) if isinstance(raw, list) else 0

    if _count("added_top_level_keys") > 0:
        return None
    if _count("removed_top_level_keys") > 0:
        return None
    if _count("changed_top_level_keys") > 0:
        return None
    unchanged_count = _count("unchanged_top_level_keys")
    if unchanged_count < 1:
        return None
    return (
        f"All top-level keys unchanged ({unchanged_count} keys; paste reproduces disk)."
    )


def full_workflow_merge_subtree_overview_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _count(block: Any, key: str) -> int:
        if not isinstance(block, Mapping):
            return 0
        raw = block.get(key)
        return len(raw) if isinstance(raw, list) else 0

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        block = subtrees.get(name)
        added = _count(block, "added_keys")
        removed = _count(block, "removed_keys")
        changed = _count(block, "changed_keys")
        unchanged = _count(block, "unchanged_keys")
        parts.append(f"{name} (+{added} / -{removed} / ~{changed} / ={unchanged})")
    return "Subtree churn: " + ", ".join(parts)


def full_workflow_merge_subtree_changed_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _segment(block_name: str) -> str | None:
        block = subtrees.get(block_name)
        if not isinstance(block, Mapping):
            return None
        raw = block.get("changed_keys")
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            trimmed = entry.strip()
            if trimmed:
                cleaned.add(trimmed)
        if not cleaned:
            return None
        ordered = sorted(cleaned)
        cap = _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS
        visible = ordered[:cap]
        overflow = len(ordered) - len(visible)
        inner = ", ".join(visible)
        if overflow > 0:
            inner += f" (+{overflow} more)"
        return f"{block_name} ({inner})"

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        seg = _segment(name)
        if seg:
            parts.append(seg)
    if not parts:
        return None
    return "Subtree changed fields: " + ", ".join(parts) + "."


def full_workflow_merge_subtree_removed_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _segment(block_name: str) -> str | None:
        block = subtrees.get(block_name)
        if not isinstance(block, Mapping):
            return None
        raw = block.get("removed_keys")
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            trimmed = entry.strip()
            if trimmed:
                cleaned.add(trimmed)
        if not cleaned:
            return None
        ordered = sorted(cleaned)
        cap = _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS
        visible = ordered[:cap]
        overflow = len(ordered) - len(visible)
        inner = ", ".join(visible)
        if overflow > 0:
            inner += f" (+{overflow} more)"
        return f"{block_name} ({inner})"

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        seg = _segment(name)
        if seg:
            parts.append(seg)
    if not parts:
        return None
    return "Subtree removed fields: " + ", ".join(parts) + "."


def full_workflow_merge_subtree_added_fields_caption(
    diff: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(diff, Mapping) or diff.get("error"):
        return None
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, Mapping):
        return None

    def _segment(block_name: str) -> str | None:
        block = subtrees.get(block_name)
        if not isinstance(block, Mapping):
            return None
        raw = block.get("added_keys")
        if not isinstance(raw, list) or not raw:
            return None
        cleaned: set[str] = set()
        for entry in raw:
            if not isinstance(entry, str):
                continue
            trimmed = entry.strip()
            if trimmed:
                cleaned.add(trimmed)
        if not cleaned:
            return None
        ordered = sorted(cleaned)
        cap = _SUBTREE_CHANGED_FIELDS_CAPTION_MAX_KEYS
        visible = ordered[:cap]
        overflow = len(ordered) - len(visible)
        inner = ", ".join(visible)
        if overflow > 0:
            inner += f" (+{overflow} more)"
        return f"{block_name} ({inner})"

    parts: list[str] = []
    for name in ("integrator_gate", "agent_evaluator"):
        seg = _segment(name)
        if seg:
            parts.append(seg)
    if not parts:
        return None
    return "Subtree added fields: " + ", ".join(parts) + "."


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


