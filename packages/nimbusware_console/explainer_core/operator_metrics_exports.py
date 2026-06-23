from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)


class WorkflowExplainerOperatorMetricsExports:
    def __init__(self, export_slug: str) -> None:
        self._export_slug = export_slug

    def export_json(self, metrics: Mapping[str, Any] | None) -> str:
        return mapping_export_json(metrics)

    def table_rows_csv(self, rows: Sequence[Mapping[str, str]]) -> str:
        return field_value_table_rows_csv(rows)

    def export_filename_slug(self) -> str:
        return self._export_slug


def bind_operator_metrics_exports(
    *,
    export_slug: str,
) -> tuple[
    Callable[[Mapping[str, Any] | None], str],
    Callable[[Sequence[Mapping[str, str]]], str],
    Callable[[], str],
]:
    exports = WorkflowExplainerOperatorMetricsExports(export_slug)
    return (
        exports.export_json,
        exports.table_rows_csv,
        exports.export_filename_slug,
    )


def install_named_operator_metrics_exports(
    namespace: dict[str, object],
    prefix: str,
    *,
    export_slug: str | None = None,
) -> tuple[
    Callable[[Mapping[str, Any] | None], str],
    Callable[[Sequence[Mapping[str, str]]], str],
    Callable[[], str],
]:
    slug = export_slug or f"{prefix}_operator_metrics"
    exports = WorkflowExplainerOperatorMetricsExports(slug)
    export_json = exports.export_json
    table_rows_csv = exports.table_rows_csv
    export_filename_slug = exports.export_filename_slug
    namespace[f"{prefix}_operator_metrics_export_json"] = export_json
    namespace[f"{prefix}_operator_metrics_table_rows_csv"] = table_rows_csv
    namespace[f"{prefix}_operator_metrics_export_filename_slug"] = export_filename_slug
    return export_json, table_rows_csv, export_filename_slug
