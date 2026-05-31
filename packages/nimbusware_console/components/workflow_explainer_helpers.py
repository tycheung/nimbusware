from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from nimbusware_console.components.explainer_panel import render_operator_metrics_explainer
from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
)


def relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def json_safe_yaml_fragment(raw: object) -> object:
    if raw is None or isinstance(raw, (bool, int, float, str)):
        return raw
    if isinstance(raw, dict):
        out: dict[str, Any] = {}
        for key, value in raw.items():
            sk = key if isinstance(key, str) else str(key)
            out[sk] = json_safe_yaml_fragment(value)
        return out
    if isinstance(raw, list):
        return [json_safe_yaml_fragment(item) for item in raw]
    return str(raw)


def env_var_tri_state_summary(name: str) -> dict[str, Any]:
    raw = os.environ.get(name, "")
    low = raw.strip().lower()
    if not low:
        return {"raw": raw, "forces_off": False, "forces_on": False, "unset": True}
    if low in ("0", "false", "no"):
        return {"raw": raw, "forces_off": True, "forces_on": False, "unset": False}
    if low in ("1", "true", "yes"):
        return {"raw": raw, "forces_off": False, "forces_on": True, "unset": False}
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset": True,
        "unrecognised_value": True,
    }


def workflow_explainer_export_json(metrics: Mapping[str, Any] | None) -> str:
    return mapping_export_json(metrics)


def workflow_explainer_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    return field_value_table_rows_csv(rows)


def workflow_explainer_export_filename_slug(slug: str) -> str:
    return slug


def render_workflow_explainer_metrics_panel(
    payload: Mapping[str, Any] | None,
    *,
    metrics_fn: Callable[[Mapping[str, Any] | None], dict[str, Any]],
    metrics_table_rows_fn: Callable[[Mapping[str, Any] | None], list[dict[str, str]]],
    metrics_caption_fn: Callable[[Mapping[str, Any] | None], str | None],
    filename_slug: str,
    json_label: str,
    csv_label: str,
    json_download_key: str,
    csv_download_key: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    metrics = metrics_fn(payload)
    rows = metrics_table_rows_fn(metrics)
    render_operator_metrics_explainer(
        caption=metrics_caption_fn(metrics),
        table_rows=rows,
        json_text=workflow_explainer_export_json(metrics),
        csv_text=workflow_explainer_table_rows_csv(rows),
        filename_slug=workflow_explainer_export_filename_slug(filename_slug),
        json_label=json_label,
        csv_label=csv_label,
        json_download_key=json_download_key,
        csv_download_key=csv_download_key,
    )
    return metrics, rows


def explainer_table_rows_from_payload(
    payload: Mapping[str, Any] | None,
    cell: Callable[[Any], str] | None = None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(payload, cell)
