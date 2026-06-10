from __future__ import annotations

from collections.abc import Mapping, Sequence

from nimbusware_console.explainer_core.workflow_exports import (
    explainer_json_cell,
    workflow_explainer_payload_export_json,
    workflow_explainer_payload_table_rows,
    workflow_explainer_payload_table_rows_csv,
)

_escalation_suppress_explainer_cell = explainer_json_cell


def escalation_policy_export_filename_slug() -> str:
    return "escalation_policy"


def escalation_suppress_export_filename_slug() -> str:
    return "escalation_suppress"


def escalation_suppress_explainer_table_rows(
    payload: Mapping[str, object] | None,
) -> list[dict[str, str]]:
    return workflow_explainer_payload_table_rows(payload)


def escalation_suppress_explainer_export_json(payload: Mapping[str, object] | None) -> str:
    return workflow_explainer_payload_export_json(payload)


def escalation_suppress_explainer_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return workflow_explainer_payload_table_rows_csv(rows)
