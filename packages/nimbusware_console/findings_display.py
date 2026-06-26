from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from functools import partial
from io import StringIO
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.components.operator_metrics import table_rows_csv
from nimbusware_console.explainer_core.metrics_scaffold import metrics_caption, metrics_table_rows
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports
from nimbusware_console.explainer_core.schema_metrics import build_operator_metrics

_FINDINGS_TABLE_COLUMNS: tuple[str, ...] = (
    "#",
    "severity",
    "category",
    "owner_role",
    "source_artifact",
    "finding_id",
    "event_id",
    "occurred_at",
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def findings_list_from_response(body: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(body, Mapping):
        return []
    raw = body.get("findings")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def findings_table_rows(findings: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, ev in enumerate(findings, start=1):
        pl = ev.get("payload")
        payload = pl if isinstance(pl, dict) else {}
        rows.append(
            {
                "#": str(i),
                "severity": _stringify(payload.get("severity")),
                "category": _stringify(payload.get("category")),
                "owner_role": _stringify(payload.get("owner_role")),
                "source_artifact": _stringify(payload.get("source_artifact")),
                "finding_id": _stringify(payload.get("finding_id")),
                "event_id": _stringify(ev.get("event_id")),
                "occurred_at": _stringify(ev.get("occurred_at")),
            },
        )
    return rows


_FINDINGS_OPERATOR_METRICS_DEFAULTS: dict[str, Any] = {
    "finding_count": 0,
    "severity_blocker": 0,
    "severity_high": 0,
    "severity_medium": 0,
    "severity_low": 0,
    "severity_other": 0,
    "distinct_categories": 0,
}

_FINDINGS_OPERATOR_METRICS_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Finding count", "finding_count"),
    ("Distinct categories", "distinct_categories"),
)

_FINDINGS_SEVERITY_ROWS: tuple[tuple[str, str], ...] = (
    ("BLOCKER", "severity_blocker"),
    ("HIGH", "severity_high"),
    ("MEDIUM", "severity_medium"),
    ("LOW", "severity_low"),
    ("Other severity", "severity_other"),
)


def findings_operator_metrics(
    findings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    metrics = build_operator_metrics(None, _FINDINGS_OPERATOR_METRICS_DEFAULTS)
    categories: set[str] = set()
    for ev in findings:
        if not isinstance(ev, Mapping):
            continue
        pl = ev.get("payload")
        payload = pl if isinstance(pl, dict) else {}
        metrics["finding_count"] = int(metrics["finding_count"]) + 1
        sev = payload.get("severity")
        if isinstance(sev, str):
            key = sev.strip().upper()
            if key == "BLOCKER":
                metrics["severity_blocker"] = int(metrics["severity_blocker"]) + 1
            elif key == "HIGH":
                metrics["severity_high"] = int(metrics["severity_high"]) + 1
            elif key == "MEDIUM":
                metrics["severity_medium"] = int(metrics["severity_medium"]) + 1
            elif key == "LOW":
                metrics["severity_low"] = int(metrics["severity_low"]) + 1
            else:
                metrics["severity_other"] = int(metrics["severity_other"]) + 1
        cat = payload.get("category")
        if isinstance(cat, str) and cat.strip():
            categories.add(cat.strip())
    metrics["distinct_categories"] = len(categories)
    return metrics


def findings_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows = metrics_table_rows(
        metrics,
        _FINDINGS_OPERATOR_METRICS_TABLE_ROWS,
        bool_lower=False,
    )
    rows.extend(
        metrics_table_rows(
            metrics,
            _FINDINGS_SEVERITY_ROWS,
            bool_lower=False,
            include_when=lambda _m, k: (
                isinstance(metrics.get(k), int)
                and not isinstance(metrics.get(k), bool)
                and int(metrics[k]) > 0
            ),
        ),
    )
    return rows


def findings_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    fc = metrics.get("finding_count")
    if isinstance(fc, bool) or not isinstance(fc, int) or fc < 1:
        return None
    parts = [f"**{fc}** finding(s)"]
    dc = metrics.get("distinct_categories", 0)
    if is_strict_int(dc):
        parts.append(f"**{dc}** distinct categor{'y' if dc == 1 else 'ies'}")
    for bucket, label in (
        ("severity_blocker", "BLOCKER"),
        ("severity_high", "HIGH"),
        ("severity_medium", "MEDIUM"),
        ("severity_low", "LOW"),
    ):
        n = metrics.get(bucket, 0)
        if is_strict_int(n) and n > 0:
            parts.append(f"**{n}** {label}")
    return metrics_caption("Findings: ", parts)


def findings_empty_caption() -> str:
    return "No finding.created events for this run."


def findings_export_json(body: Mapping[str, Any] | None) -> str:
    if not isinstance(body, Mapping):
        return "{}"
    return json.dumps(dict(body), indent=2, ensure_ascii=False)


findings_table_rows_csv = partial(table_rows_csv, columns=_FINDINGS_TABLE_COLUMNS)


def findings_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def findings_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return findings_export_filename_slug(run_id, max_len=max_len)


(
    findings_operator_metrics_export_json,
    findings_operator_metrics_table_rows_csv,
    _findings_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="findings_operator_metrics")
