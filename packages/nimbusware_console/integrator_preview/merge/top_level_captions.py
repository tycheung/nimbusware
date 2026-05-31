from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


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


