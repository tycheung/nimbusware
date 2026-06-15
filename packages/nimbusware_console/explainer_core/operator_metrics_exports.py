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
