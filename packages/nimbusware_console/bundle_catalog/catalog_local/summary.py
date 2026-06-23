from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,
    _bundle_catalog_local_summary_cell,
)
from nimbusware_console.bundle_catalog.catalog_local._constants import (
    _LOCAL_CATALOG_RELPATH,
)
from nimbusware_console.bundle_catalog.catalog_local._load import (
    catalog_bundle_rows,
    catalog_yaml_path,
    load_catalog_doc,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports


def bundle_catalog_local_summary(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    doc = load_catalog_doc(repo_root, config_materializer=config_materializer)
    path = catalog_yaml_path(repo_root)
    has = doc is not None
    out: dict[str, Any] = {
        "has_catalog_yaml": has,
        "catalog_yaml_relpath": _LOCAL_CATALOG_RELPATH if has else None,
        "bundle_count": 0,
        "distinct_tag_count": 0,
    }
    if doc is None:
        if path.is_file():
            out["has_catalog_yaml"] = True
            out["catalog_yaml_relpath"] = _LOCAL_CATALOG_RELPATH
        return out
    dict_rows = catalog_bundle_rows(doc)
    out["bundle_count"] = len(dict_rows)
    tags: set[str] = set()
    for b in dict_rows:
        raw_tags = b.get("tags")
        if not isinstance(raw_tags, list):
            continue
        for t in raw_tags:
            if isinstance(t, str) and t.strip():
                tags.add(t.strip())
    out["distinct_tag_count"] = len(tags)
    return out


def bundle_catalog_local_summary_export_filename_slug() -> str:
    return "bundle_catalog_local_summary"


def bundle_catalog_local_summary_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in summary.keys()):
        rows.append(
            {
                "field": key,
                "value": _bundle_catalog_local_summary_cell(summary.get(key)),
            },
        )
    return rows


def bundle_catalog_local_summary_export_json(
    summary: Mapping[str, Any] | None,
) -> str:
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), indent=2, ensure_ascii=False)


def bundle_catalog_local_summary_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def bundle_catalog_local_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "has_catalog_yaml": False,
        "catalog_yaml_present": False,
        "bundle_count": 0,
        "distinct_tag_count": 0,
        "avg_tags_per_bundle": 0.0,
    }
    if not isinstance(summary, Mapping):
        return metrics
    has_yaml = summary.get("has_catalog_yaml") is True
    metrics["has_catalog_yaml"] = has_yaml
    metrics["catalog_yaml_present"] = has_yaml
    bc = summary.get("bundle_count")
    if isinstance(bc, int) and not isinstance(bc, bool) and bc >= 0:
        metrics["bundle_count"] = bc
    dtc = summary.get("distinct_tag_count")
    if isinstance(dtc, int) and not isinstance(dtc, bool) and dtc >= 0:
        metrics["distinct_tag_count"] = dtc
    if metrics["bundle_count"] > 0:
        metrics["avg_tags_per_bundle"] = round(
            metrics["distinct_tag_count"] / metrics["bundle_count"],
            2,
        )
    return metrics


def bundle_catalog_local_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Catalog YAML present",
            "value": str(metrics.get("catalog_yaml_present", False)).lower(),
        },
        {"field": "Bundle count", "value": str(metrics.get("bundle_count", 0))},
        {
            "field": "Distinct tag count",
            "value": str(metrics.get("distinct_tag_count", 0)),
        },
    ]
    avg = metrics.get("avg_tags_per_bundle")
    if isinstance(avg, (int, float)) and not isinstance(avg, bool):
        rows.append({"field": "Distinct tags / bundle", "value": str(avg)})
    return rows


(
    bundle_catalog_local_summary_operator_metrics_export_json,
    bundle_catalog_local_summary_operator_metrics_table_rows_csv,
    bundle_catalog_local_summary_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(export_slug="bundle_catalog_local_summary_operator_metrics")


def bundle_catalog_local_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("catalog_yaml_present") is not True:
        return None
    bc = metrics.get("bundle_count", 0)
    dtc = metrics.get("distinct_tag_count", 0)
    if not isinstance(bc, int) or isinstance(bc, bool):
        bc = 0
    if not isinstance(dtc, int) or isinstance(dtc, bool):
        dtc = 0
    return f"Local catalog operator metrics: **{bc}** bundle(s), **{dtc}** distinct tag(s)."
