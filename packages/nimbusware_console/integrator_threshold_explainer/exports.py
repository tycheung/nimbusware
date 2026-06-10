from __future__ import annotations

from collections.abc import Mapping, Sequence

from nimbusware_console.explainer_core.workflow_exports import (
    explainer_json_cell,
    workflow_explainer_payload_export_json,
    workflow_explainer_payload_table_rows,
    workflow_explainer_payload_table_rows_csv,
)

_integrator_threshold_explainer_cell = explainer_json_cell


def integrator_threshold_export_filename_slug() -> str:
    return "integrator_threshold"


def integrator_threshold_explainer_table_rows(
    payload: Mapping[str, object] | None,
) -> list[dict[str, str]]:
    return workflow_explainer_payload_table_rows(payload)


def integrator_threshold_explainer_export_json(payload: Mapping[str, object] | None) -> str:
    return workflow_explainer_payload_export_json(payload)


def integrator_threshold_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return workflow_explainer_payload_table_rows_csv(rows)
