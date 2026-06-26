from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,
    _bundle_catalog_local_summary_cell,
)
from nimbusware_console.bundle_catalog.catalog_local._load import (
    catalog_bundle_rows,
    load_catalog_doc,
)
from nimbusware_console.bundle_catalog.catalog_local.summary import (
    bundle_catalog_local_summary,
)
from nimbusware_console.components.operator_metrics import (
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports


def bundle_catalog_bundles_without_id_rollup(repo_root: Path) -> dict[str, Any]:
    summary = bundle_catalog_local_summary(repo_root)
    without = bundle_catalog_bundles_without_id_count(repo_root)
    total = summary.get("bundle_count")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = 0
    return {
        "has_catalog_yaml": summary.get("has_catalog_yaml"),
        "catalog_yaml_relpath": summary.get("catalog_yaml_relpath"),
        "bundle_count": total,
        "distinct_tag_count": summary.get("distinct_tag_count"),
        "bundles_without_id_count": without,
        "bundles_with_id_count": max(total - without, 0),
    }


def bundle_catalog_bundles_without_id_rollup_export_filename_slug() -> str:
    return "bundle_catalog_bundles_without_id"


def bundle_catalog_bundles_without_id_rollup_table_rows(
    rollup: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(rollup, _bundle_catalog_local_summary_cell)


def bundle_catalog_bundles_without_id_rollup_export_json(
    rollup: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(rollup)


bundle_catalog_bundles_without_id_rollup_table_rows_csv = partial(
    table_rows_csv,
    columns=_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,
)


def bundle_catalog_bundles_without_id_rollup_operator_metrics(
    rollup: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "has_catalog_yaml": False,
        "bundle_count": 0,
        "bundles_without_id_count": 0,
        "bundles_with_id_count": 0,
    }
    if not isinstance(rollup, Mapping):
        return metrics
    metrics["has_catalog_yaml"] = rollup.get("has_catalog_yaml") is True
    bc = rollup.get("bundle_count")
    if is_strict_int(bc) and bc >= 0:
        metrics["bundle_count"] = bc
    without = rollup.get("bundles_without_id_count")
    if is_strict_int(without) and without >= 0:
        metrics["bundles_without_id_count"] = without
    with_id = rollup.get("bundles_with_id_count")
    if is_strict_int(with_id) and with_id >= 0:
        metrics["bundles_with_id_count"] = with_id
    return metrics


def bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    return [
        {
            "field": "Catalog YAML present",
            "value": str(metrics.get("has_catalog_yaml", False)).lower(),
        },
        {"field": "Bundle count", "value": str(metrics.get("bundle_count", 0))},
        {
            "field": "Bundles without id",
            "value": str(metrics.get("bundles_without_id_count", 0)),
        },
        {
            "field": "Bundles with id",
            "value": str(metrics.get("bundles_with_id_count", 0)),
        },
    ]


(
    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv,
    bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(
    export_slug="bundle_catalog_bundles_without_id_rollup_operator_metrics",
)


def bundle_catalog_bundles_without_id_rollup_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("has_catalog_yaml") is not True:
        return None
    bc = metrics.get("bundle_count", 0)
    without = metrics.get("bundles_without_id_count", 0)
    if not isinstance(bc, int) or isinstance(bc, bool):
        bc = 0
    if not isinstance(without, int) or isinstance(without, bool):
        without = 0
    return f"Bundles without id rollup metrics: **{without}** without id of **{bc}** bundle(s)."


def bundle_catalog_bundles_without_id_caption(repo_root: Path) -> str | None:
    without = bundle_catalog_bundles_without_id_count(repo_root)
    if without <= 0:
        return None
    total = bundle_catalog_local_summary(repo_root).get("bundle_count")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        return f"Bundles without id: **{without}**."
    return f"Bundles without id: **{without}** of **{total}**."


def bundle_catalog_bundles_without_id_count(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> int:
    doc = load_catalog_doc(repo_root, config_materializer=config_materializer)
    if doc is None:
        return 0
    without = 0
    for b in catalog_bundle_rows(doc):
        raw_id = b.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            without += 1
    return without
