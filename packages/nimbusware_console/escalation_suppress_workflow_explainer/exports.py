from __future__ import annotations

from nimbusware_console.explainer_core.workflow_exports import WorkflowExplainerExports

_exp = WorkflowExplainerExports("escalation_suppress")
_escalation_suppress_explainer_cell = _exp.cell
escalation_suppress_export_filename_slug = _exp.export_filename_slug
escalation_suppress_explainer_table_rows = _exp.explainer_table_rows
escalation_suppress_explainer_export_json = _exp.explainer_export_json
escalation_suppress_explainer_table_rows_csv = _exp.explainer_table_rows_csv


def escalation_policy_export_filename_slug() -> str:
    return "escalation_policy"
