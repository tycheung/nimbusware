from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from nimbusware_console.explainer_core.workflow_explainer_registry import (
    WORKFLOW_EXPLAINER_SPECS,
    explainer_metrics_prefix,
)


@dataclass(frozen=True)
class ExplainerExportFns:
    table_rows: Callable[[Mapping[str, Any]], list[dict[str, str]]]
    export_json: Callable[[Mapping[str, Any]], str]
    table_rows_csv: Callable[[list[dict[str, str]]], str]
    export_filename_slug: Callable[[], str]
    operator_metrics: Callable[[Mapping[str, Any] | None], dict[str, Any]]
    operator_metrics_export_json: Callable[[Mapping[str, Any]], str]
    operator_metrics_export_filename_slug: Callable[[], str]
    operator_metrics_table_rows: Callable[[Mapping[str, Any]], list[dict[str, str]]]


def _explainer_short_name(slug: str) -> str:
    if slug == "integrator_threshold":
        return "integrator_threshold_explainer"
    return slug


def load_explainer_export_fns(slug: str) -> ExplainerExportFns:
    mod = importlib.import_module(f"nimbusware_console.workflow_explainers.{slug}")
    short = _explainer_short_name(slug)
    prefix = explainer_metrics_prefix(slug)
    return ExplainerExportFns(
        table_rows=getattr(mod, f"{short}_explainer_table_rows"),
        export_json=getattr(mod, f"{short}_explainer_export_json"),
        table_rows_csv=getattr(mod, f"{short}_explainer_table_rows_csv"),
        export_filename_slug=getattr(mod, f"{short}_export_filename_slug"),
        operator_metrics=getattr(mod, f"{prefix}_operator_metrics"),
        operator_metrics_export_json=getattr(
            mod,
            f"{prefix}_operator_metrics_export_json",
        ),
        operator_metrics_export_filename_slug=getattr(
            mod,
            f"{prefix}_operator_metrics_export_filename_slug",
        ),
        operator_metrics_table_rows=getattr(
            mod,
            f"{prefix}_operator_metrics_table_rows",
        ),
    )


def assert_explainer_export_contract(
    fns: ExplainerExportFns,
    payload: Mapping[str, Any],
    *,
    export_slug: str,
    required_fields: tuple[str, ...] = (),
) -> None:
    rows = fns.table_rows(payload)
    fields = {r["field"] for r in rows}
    for field in required_fields:
        assert field in fields, f"missing field {field!r} in table rows"
    assert len(rows) == len(payload)
    parsed = json.loads(fns.export_json(payload))
    assert parsed == payload
    csv_text = fns.table_rows_csv(rows)
    assert csv_text.splitlines()[0] == "field,value"
    assert fns.table_rows({}) == []  # type: ignore[arg-type]
    assert fns.table_rows_csv([]) == ""
    assert fns.export_filename_slug() == export_slug


def assert_operator_metrics_export_contract(
    fns: ExplainerExportFns,
    *,
    first_row_field: str | None = None,
    metrics_export_slug_suffix: str | None = None,
) -> None:
    m = fns.operator_metrics({})
    roundtrip = json.loads(fns.operator_metrics_export_json(m))
    assert roundtrip == m
    rows = fns.operator_metrics_table_rows(m)
    if first_row_field is not None:
        assert rows[0]["field"] == first_row_field
    slug = fns.export_filename_slug()
    expected = metrics_export_slug_suffix or f"{slug}_workflow_explainer_operator_metrics"
    assert fns.operator_metrics_export_filename_slug() == expected


def load_caption_fn(dotted: str) -> Callable[[Any], str | None]:
    module_path, _, name = dotted.rpartition(".")
    mod = importlib.import_module(module_path)
    fn = getattr(mod, name)
    if not callable(fn):
        raise TypeError(f"{dotted} is not callable")
    return fn


EXPORT_SMOKE_SLUGS = tuple(
    spec.slug
    for spec in WORKFLOW_EXPLAINER_SPECS
    if spec.slug
    not in {"integration_adapter_writer", "integrator_threshold"}
)
