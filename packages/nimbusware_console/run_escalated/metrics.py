from __future__ import annotations

from nimbusware_console.explainer_core.generic_display_metrics import (
    run_escalated_delta_operator_metrics,
    run_escalated_delta_operator_metrics_caption,
    run_escalated_delta_operator_metrics_export_json,
    run_escalated_delta_operator_metrics_table_rows,
    run_escalated_delta_operator_metrics_table_rows_csv,
    run_escalated_history_operator_metrics,
    run_escalated_history_operator_metrics_caption,
    run_escalated_history_operator_metrics_export_json,
    run_escalated_history_operator_metrics_table_rows,
    run_escalated_history_operator_metrics_table_rows_csv,
    run_escalated_operator_metrics,
    run_escalated_operator_metrics_caption,
    run_escalated_operator_metrics_export_json,
    run_escalated_operator_metrics_table_rows,
    run_escalated_operator_metrics_table_rows_csv,
)
from nimbusware_console.run_escalated.rows import (
    run_escalated_delta_export_filename_slug,
    run_escalated_export_filename_slug,
    run_escalated_history_export_filename_slug,
)


def run_escalated_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_export_filename_slug(run_id, max_len=max_len)


def run_escalated_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_history_export_filename_slug(run_id, max_len=max_len)


def run_escalated_delta_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_escalated_delta_export_filename_slug(run_id, max_len=max_len)
