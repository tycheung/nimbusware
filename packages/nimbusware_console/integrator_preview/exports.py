from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)
from nimbusware_console.integrator_preview.merge import (
    full_workflow_merge_attention_rows,
)


def full_workflow_merge_diff_export_filename_slug() -> str:
    return "full_workflow_merge_diff"



def _full_workflow_merge_diff_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def full_workflow_merge_diff_table_rows(
    diff: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(diff, Mapping):
        return []
    if diff.get("error"):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in diff.keys()):
        rows.append(
            {
                "field": key,
                "value": _full_workflow_merge_diff_cell(diff.get(key)),
            },
        )
    return rows


def full_workflow_merge_diff_export_json(
    diff: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(diff)


def full_workflow_merge_diff_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def _full_workflow_merge_diff_list_count(diff: Mapping[str, Any], key: str) -> int:
    raw = diff.get(key)
    return len(raw) if isinstance(raw, list) else 0


def full_workflow_merge_diff_operator_metrics(
    diff: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "added_top_level_count": 0,
        "removed_top_level_count": 0,
        "changed_top_level_count": 0,
        "unchanged_top_level_count": 0,
        "top_level_churn": 0,
        "subtree_diff_count": 0,
        "paste_only_top_level_count": 0,
        "disk_only_top_level_count": 0,
        "has_error": False,
    }
    if not isinstance(diff, Mapping):
        return metrics
    if diff.get("error"):
        metrics["has_error"] = True
        return metrics
    added = _full_workflow_merge_diff_list_count(diff, "added_top_level_keys")
    removed = _full_workflow_merge_diff_list_count(diff, "removed_top_level_keys")
    changed = _full_workflow_merge_diff_list_count(diff, "changed_top_level_keys")
    unchanged = _full_workflow_merge_diff_list_count(diff, "unchanged_top_level_keys")
    metrics["added_top_level_count"] = added
    metrics["removed_top_level_count"] = removed
    metrics["changed_top_level_count"] = changed
    metrics["unchanged_top_level_count"] = unchanged
    metrics["top_level_churn"] = added + removed + changed
    subtrees = diff.get("subtree_field_diffs")
    if isinstance(subtrees, dict):
        metrics["subtree_diff_count"] = len(subtrees)
    paste_only = diff.get("paste_only_top_level_keys")
    if isinstance(paste_only, list):
        metrics["paste_only_top_level_count"] = len(paste_only)
    disk_only = diff.get("disk_only_top_level_keys")
    if isinstance(disk_only, list):
        metrics["disk_only_top_level_count"] = len(disk_only)
    return metrics


def full_workflow_merge_diff_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    if metrics.get("has_error") is True:
        return [{"field": "Error", "value": "yes"}]
    return [
        {"field": "Added top-level", "value": str(metrics.get("added_top_level_count", 0))},
        {"field": "Removed top-level", "value": str(metrics.get("removed_top_level_count", 0))},
        {"field": "Changed top-level", "value": str(metrics.get("changed_top_level_count", 0))},
        {
            "field": "Unchanged top-level",
            "value": str(metrics.get("unchanged_top_level_count", 0)),
        },
        {"field": "Top-level churn", "value": str(metrics.get("top_level_churn", 0))},
        {"field": "Subtree diffs", "value": str(metrics.get("subtree_diff_count", 0))},
        {
            "field": "Paste-only top-level",
            "value": str(metrics.get("paste_only_top_level_count", 0)),
        },
        {
            "field": "Disk-only top-level",
            "value": str(metrics.get("disk_only_top_level_count", 0)),
        },
    ]


def full_workflow_merge_diff_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("has_error") is True:
        return None
    added = metrics.get("added_top_level_count", 0)
    removed = metrics.get("removed_top_level_count", 0)
    changed = metrics.get("changed_top_level_count", 0)
    unchanged = metrics.get("unchanged_top_level_count", 0)
    if not all(
        isinstance(x, int) and not isinstance(x, bool)
        for x in (added, removed, changed, unchanged)
    ):
        return None
    paste_only = metrics.get("paste_only_top_level_count", 0)
    disk_only = metrics.get("disk_only_top_level_count", 0)
    base = (
        f"Merge diff operator metrics: Top-level: +{added} / -{removed} / "
        f"~{changed} / ={unchanged}."
    )
    hints: list[str] = []
    if isinstance(paste_only, int) and not isinstance(paste_only, bool) and paste_only > 0:
        hints.append(f"**{paste_only}** paste-only key(s)")
    if isinstance(disk_only, int) and not isinstance(disk_only, bool) and disk_only > 0:
        hints.append(f"**{disk_only}** disk-only key(s)")
    if hints:
        return base[:-1] + "; " + ", ".join(hints) + "."
    return base



def full_workflow_merge_diff_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def full_workflow_merge_diff_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def full_workflow_merge_diff_operator_metrics_export_filename_slug() -> str:
    return "full_workflow_merge_diff_operator_metrics"


def full_workflow_merge_attention_export_filename_slug() -> str:
    return "full_workflow_merge_attention"


_FULL_WORKFLOW_MERGE_ATTENTION_CSV_COLUMNS: tuple[str, ...] = ("flag", "keys")


def full_workflow_merge_attention_export_json(
    rows: Sequence[Mapping[str, str]],
) -> str:
    out = [dict(r) for r in rows if isinstance(r, Mapping)]
    return json.dumps(out, indent=2, ensure_ascii=False)


def full_workflow_merge_attention_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_FULL_WORKFLOW_MERGE_ATTENTION_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _FULL_WORKFLOW_MERGE_ATTENTION_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def _full_workflow_merge_attention_subtree_row_count(diff: Mapping[str, Any]) -> int:
    subtrees = diff.get("subtree_field_diffs")
    if not isinstance(subtrees, dict):
        return 0
    removed_any = False
    added_any = False
    changed_any = False
    for name in ("integrator_gate", "agent_evaluator"):
        inner = subtrees.get(name)
        if not isinstance(inner, dict):
            continue
        if isinstance(inner.get("removed_keys"), list) and inner.get("removed_keys"):
            removed_any = True
        if isinstance(inner.get("added_keys"), list) and inner.get("added_keys"):
            added_any = True
        if isinstance(inner.get("changed_keys"), list) and inner.get("changed_keys"):
            changed_any = True
    return int(removed_any) + int(added_any) + int(changed_any)


def full_workflow_merge_attention_operator_metrics(
    diff: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "attention_row_count": 0,
        "has_removed_top_level": False,
        "has_added_top_level": False,
        "has_disk_only_keys": False,
        "has_paste_only_keys": False,
        "has_dual_subtree_change": False,
        "subtree_attention_row_count": 0,
        "has_error": False,
    }
    if not isinstance(diff, Mapping):
        return metrics
    if diff.get("error"):
        metrics["has_error"] = True
        return metrics
    rows = full_workflow_merge_attention_rows(diff)
    metrics["attention_row_count"] = len(rows)
    removed = diff.get("removed_top_level_keys")
    metrics["has_removed_top_level"] = isinstance(removed, list) and bool(removed)
    added = diff.get("added_top_level_keys")
    metrics["has_added_top_level"] = isinstance(added, list) and bool(added)
    disk_only = diff.get("disk_only_top_level_keys")
    metrics["has_disk_only_keys"] = isinstance(disk_only, list) and bool(disk_only)
    paste_only = diff.get("paste_only_top_level_keys")
    metrics["has_paste_only_keys"] = isinstance(paste_only, list) and bool(paste_only)
    changed = diff.get("changed_top_level_keys")
    if isinstance(changed, list):
        metrics["has_dual_subtree_change"] = (
            "integrator_gate" in changed and "agent_evaluator" in changed
        )
    metrics["subtree_attention_row_count"] = _full_workflow_merge_attention_subtree_row_count(
        diff,
    )
    return metrics


def full_workflow_merge_attention_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    if metrics.get("has_error") is True:
        return [{"field": "Error", "value": "yes"}]
    return [
        {
            "field": "Attention row count",
            "value": str(metrics.get("attention_row_count", 0)),
        },
        {
            "field": "Removed top-level",
            "value": str(metrics.get("has_removed_top_level", False)).lower(),
        },
        {
            "field": "Added top-level",
            "value": str(metrics.get("has_added_top_level", False)).lower(),
        },
        {
            "field": "Disk-only keys",
            "value": str(metrics.get("has_disk_only_keys", False)).lower(),
        },
        {
            "field": "Paste-only keys",
            "value": str(metrics.get("has_paste_only_keys", False)).lower(),
        },
        {
            "field": "Dual subtree change",
            "value": str(metrics.get("has_dual_subtree_change", False)).lower(),
        },
        {
            "field": "Subtree attention rows",
            "value": str(metrics.get("subtree_attention_row_count", 0)),
        },
    ]


def full_workflow_merge_attention_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("has_error") is True:
        return None
    n = metrics.get("attention_row_count", 0)
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        return None
    word = "hint" if n == 1 else "hints"
    return f"Full-workflow merge attention metrics: **{n}** attention {word}."



def full_workflow_merge_attention_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def full_workflow_merge_attention_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def full_workflow_merge_attention_operator_metrics_export_filename_slug() -> str:
    return "full_workflow_merge_attention_operator_metrics"
