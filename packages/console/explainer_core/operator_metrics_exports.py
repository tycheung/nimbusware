from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from console.components.operator_metrics import mapping_export_json
from console.explainer_core.metrics_scaffold import metrics_caption, metrics_table_rows
from console.explainer_core.schema_metrics import build_operator_metrics
from console.explainer_core.table_rows_csv import field_value_table_rows_csv


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


MetricsFn = Callable[[Any], dict[str, Any]]
TableRowsFn = Callable[[Any], list[dict[str, str]]]
CaptionFn = Callable[[Any], str | None]
IncludeWhen = Callable[[Mapping[str, Any], str], bool]


def install_operator_metrics_module(
    namespace: dict[str, object],
    *,
    module_prefix: str,
    metrics: MetricsFn,
    table_rows: TableRowsFn,
    caption: CaptionFn,
    export_slug: str | None = None,
) -> Any:
    namespace[f"{module_prefix}_operator_metrics"] = metrics
    namespace[f"{module_prefix}_operator_metrics_table_rows"] = table_rows
    namespace[f"{module_prefix}_operator_metrics_caption"] = caption
    export_json, table_rows_csv, export_filename_slug = install_named_operator_metrics_exports(
        namespace,
        module_prefix,
        export_slug=export_slug or f"{module_prefix}_operator_metrics",
    )
    return metrics, table_rows, caption, export_json, table_rows_csv, export_filename_slug


def build_metrics_fn(
    defaults: Mapping[str, Any],
    *,
    postprocess: Callable[[dict[str, Any], Mapping[str, Any] | None], dict[str, Any]] | None = None,
    **build_kwargs: Any,
) -> MetricsFn:
    def metrics(payload: Mapping[str, Any] | None) -> dict[str, Any]:
        out = build_operator_metrics(payload, defaults, **build_kwargs)
        if postprocess is not None and isinstance(payload, Mapping):
            return postprocess(out, payload)
        return out

    return metrics


def table_rows_fn(
    rows: Sequence[tuple[str, str]],
    *,
    include_when: IncludeWhen | None = None,
    append_load_error_row: bool = False,
    exclude_keys: frozenset[str] = frozenset(),
) -> TableRowsFn:
    spec = [r for r in rows if r[1] not in exclude_keys]

    def table_rows(metrics: Mapping[str, Any] | None) -> list[dict[str, str]]:
        out = metrics_table_rows(metrics, spec, include_when=include_when)
        if (
            append_load_error_row
            and isinstance(metrics, Mapping)
            and metrics.get("load_error_present")
        ):
            out.append({"field": "Load error", "value": "yes"})
        return out

    return table_rows


def caption_from_parts(
    prefix: str, parts_fn: Callable[[Mapping[str, Any]], Sequence[str]]
) -> CaptionFn:
    def caption(metrics: Mapping[str, Any] | None) -> str | None:
        if not isinstance(metrics, Mapping):
            return None
        return metrics_caption(prefix, list(parts_fn(metrics)))

    return caption
