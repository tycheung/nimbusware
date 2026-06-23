from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports
from nimbusware_console.security_scan_on_verify._helpers import (
    _SECURITY_SCAN_ON_VERIFY_FIELDS,
    _stringify,
)


def security_scan_on_verify_summary_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _SECURITY_SCAN_ON_VERIFY_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


_SECURITY_SCAN_ON_VERIFY_LATEST_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def security_scan_on_verify_latest_summary_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SECURITY_SCAN_ON_VERIFY_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SECURITY_SCAN_ON_VERIFY_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def security_scan_on_verify_latest_export_json(
    summary: Mapping[str, Any] | None,
) -> str:
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), ensure_ascii=False, indent=2)


def security_scan_on_verify_latest_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def _security_scan_snippet_char_len(summary: Mapping[str, Any]) -> int:
    sn = summary.get("security_scan_snippet")
    if not isinstance(sn, str):
        return 0
    return len(sn.strip())


def security_scan_on_verify_latest_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "category_present": False,
        "severity_present": False,
        "snippet_char_len": 0,
        "finding_id_present": False,
        "event_id_present": False,
        "security_scan_ruff_exit": None,
        "security_scan_bandit_exit": None,
    }
    if not isinstance(summary, Mapping):
        return metrics
    cat = summary.get("category")
    metrics["category_present"] = isinstance(cat, str) and bool(cat.strip())
    sev = summary.get("severity")
    metrics["severity_present"] = isinstance(sev, str) and bool(sev.strip())
    metrics["snippet_char_len"] = _security_scan_snippet_char_len(summary)
    fid = summary.get("finding_id")
    metrics["finding_id_present"] = isinstance(fid, str) and bool(fid.strip())
    eid = summary.get("event_id")
    metrics["event_id_present"] = isinstance(eid, str) and bool(eid.strip())
    for key in ("security_scan_ruff_exit", "security_scan_bandit_exit"):
        val = summary.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            metrics[key] = int(val)
    return metrics


def security_scan_on_verify_latest_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("category_present") is True:
        rows.append({"field": "Category present", "value": "yes"})
    if metrics.get("severity_present") is True:
        rows.append({"field": "Severity present", "value": "yes"})
    scl = metrics.get("snippet_char_len", 0)
    if isinstance(scl, int) and not isinstance(scl, bool) and scl > 0:
        rows.append({"field": "Snippet length (chars)", "value": str(scl)})
    if metrics.get("finding_id_present") is True:
        rows.append({"field": "Finding id present", "value": "yes"})
    if metrics.get("event_id_present") is True:
        rows.append({"field": "Event id present", "value": "yes"})
    for key, label in (
        ("security_scan_ruff_exit", "Ruff exit code"),
        ("security_scan_bandit_exit", "Bandit exit code"),
    ):
        val = metrics.get(key)
        if isinstance(val, int) and not isinstance(val, bool):
            rows.append({"field": label, "value": str(val)})
    return rows


def security_scan_on_verify_latest_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("category_present") is True:
        parts.append("category")
    if metrics.get("severity_present") is True:
        parts.append("severity")
    scl = metrics.get("snippet_char_len", 0)
    if isinstance(scl, int) and not isinstance(scl, bool) and scl > 0:
        parts.append(f"**{scl}**-char snippet")
    if metrics.get("finding_id_present") is True:
        parts.append("finding id")
    ruff = metrics.get("security_scan_ruff_exit")
    if isinstance(ruff, int) and not isinstance(ruff, bool):
        parts.append(f"ruff_exit={ruff}")
    bandit = metrics.get("security_scan_bandit_exit")
    if isinstance(bandit, int) and not isinstance(bandit, bool):
        parts.append(f"bandit_exit={bandit}")
    if not parts:
        return None
    return "Security scan finding metrics: " + ", ".join(parts) + "."


(
    security_scan_on_verify_latest_operator_metrics_export_json,
    security_scan_on_verify_latest_operator_metrics_table_rows_csv,
    _security_scan_on_verify_latest_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(
    export_slug="security_scan_on_verify_latest_operator_metrics",
)


def security_scan_on_verify_latest_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return security_scan_on_verify_latest_export_filename_slug(run_id, max_len=max_len)


(
    security_scan_linter_operator_metrics_export_json,
    security_scan_linter_operator_metrics_table_rows_csv,
    _security_scan_linter_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="security_scan_linter_operator_metrics")


def security_scan_linter_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return security_scan_on_verify_latest_export_filename_slug(run_id, max_len=max_len)
