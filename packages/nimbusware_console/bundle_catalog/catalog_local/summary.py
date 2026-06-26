from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from pathlib import Path
from typing import Any

from agent_core.coercion import is_number, is_strict_int
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
from nimbusware_console.components.operator_metrics import (
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    install_operator_metrics_module,
    table_rows_fn,
)


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
    return mapping_to_sorted_table_rows(summary, _bundle_catalog_local_summary_cell)


def bundle_catalog_local_summary_export_json(
    summary: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(summary)


bundle_catalog_local_summary_table_rows_csv = partial(
    table_rows_csv,
    columns=_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS,
)


_LOCAL_SUMMARY_PREFIX = "bundle_catalog_local_summary"

_LOCAL_SUMMARY_DEFAULTS: dict[str, Any] = {
    "has_catalog_yaml": False,
    "catalog_yaml_present": False,
    "bundle_count": 0,
    "distinct_tag_count": 0,
    "avg_tags_per_bundle": 0.0,
}

_LOCAL_SUMMARY_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Catalog YAML present", "catalog_yaml_present"),
    ("Bundle count", "bundle_count"),
    ("Distinct tag count", "distinct_tag_count"),
    ("Distinct tags / bundle", "avg_tags_per_bundle"),
)


def _local_summary_postprocess(
    metrics: dict[str, Any],
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics["catalog_yaml_present"] = metrics["has_catalog_yaml"]
    if metrics["bundle_count"] > 0:
        metrics["avg_tags_per_bundle"] = round(
            metrics["distinct_tag_count"] / metrics["bundle_count"],
            2,
        )
    return metrics


def _local_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return table_rows_fn(
        _LOCAL_SUMMARY_TABLE_ROWS,
        include_when=lambda _m, key: key != "avg_tags_per_bundle" or is_number(_m.get(key)),
    )(metrics)


def _local_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping) or metrics.get("catalog_yaml_present") is not True:
        return None
    bc = metrics.get("bundle_count", 0)
    dtc = metrics.get("distinct_tag_count", 0)
    if not is_strict_int(bc):
        bc = 0
    if not is_strict_int(dtc):
        dtc = 0
    return f"Local catalog operator metrics: **{bc}** bundle(s), **{dtc}** distinct tag(s)."


(
    bundle_catalog_local_summary_operator_metrics,
    bundle_catalog_local_summary_operator_metrics_table_rows,
    bundle_catalog_local_summary_operator_metrics_caption,
    bundle_catalog_local_summary_operator_metrics_export_json,
    bundle_catalog_local_summary_operator_metrics_table_rows_csv,
    _bundle_catalog_local_summary_operator_metrics_export_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_LOCAL_SUMMARY_PREFIX,
    metrics=build_metrics_fn(
        _LOCAL_SUMMARY_DEFAULTS,
        bool_fields=(("has_catalog_yaml", "has_catalog_yaml"),),
        int_fields=(
            ("bundle_count", "bundle_count"),
            ("distinct_tag_count", "distinct_tag_count"),
        ),
        postprocess=_local_summary_postprocess,
    ),
    table_rows=_local_summary_operator_metrics_table_rows,
    caption=_local_summary_operator_metrics_caption,
)
