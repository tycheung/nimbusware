from __future__ import annotations

from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import datetime, st, timezone
from nimbusware_console.pages.run_detail._imports_display_a import (
    integrator_gate_compatibility_ranking_caption,
    integrator_gate_compatibility_ranking_table_rows,
    integrator_gate_delta_bundle_changed_caption,
    integrator_gate_delta_export_filename_slug,
    integrator_gate_delta_export_json,
    integrator_gate_delta_from_timeline,
    integrator_gate_delta_operator_metrics,
    integrator_gate_delta_operator_metrics_caption,
    integrator_gate_delta_operator_metrics_export_json,
    integrator_gate_delta_operator_metrics_table_rows_csv,
    integrator_gate_delta_operator_table_rows,
    integrator_gate_delta_summary_rows,
    integrator_gate_delta_summary_rows_csv,
    integrator_gate_delta_transition_caption,
    integrator_gate_delta_verdict_changed_caption,
    integrator_gate_from_timeline,
    integrator_gate_history_distinct_bundles_caption,
    integrator_gate_history_entry_count_caption,
    integrator_gate_history_export_filename_slug,
    integrator_gate_history_export_json,
    integrator_gate_history_failure_reason_caption,
    integrator_gate_history_from_timeline,
    integrator_gate_history_latest_margin_caption,
    integrator_gate_history_metrics_table_rows,
    integrator_gate_history_operator_metrics,
    integrator_gate_history_operator_metrics_caption,
    integrator_gate_history_operator_metrics_export_json,
    integrator_gate_history_operator_metrics_table_rows_csv,
    integrator_gate_history_score_range_caption,
    integrator_gate_history_table_rows,
    integrator_gate_history_table_rows_csv,
    integrator_gate_history_verdict_tally_caption,
    integrator_gate_latest_bundle_id_caption,
    integrator_gate_latest_export_filename_slug,
    integrator_gate_latest_export_json,
    integrator_gate_latest_metrics_table_rows,
    integrator_gate_latest_operator_metrics,
    integrator_gate_latest_operator_metrics_caption,
    integrator_gate_latest_operator_metrics_export_json,
    integrator_gate_latest_operator_metrics_table_rows_csv,
    integrator_gate_latest_score_margin_caption,
    integrator_gate_latest_summary_rows_csv,
    integrator_gate_latest_tag_overlap_caption,
    integrator_gate_summary_rows,
)



def _render_integrator_gate_history(run_id: str, data: dict) -> None:
    with st.expander("Integrator gate history (from timeline)", expanded=False):
        if not _ig_hist_rows:
            st.caption(
                "No ``integrator_gate_history`` on this timeline (same condition as "
                "empty latest summary — no integrator gate decisions recorded)."
            )
        else:
            st.caption(
                "Chronological ``gate.decision.emitted`` rows with integrator metadata "
                "(bounded on the API; latest row matches **Integrator gate** summary)."
            )
            _ig_hist_count_cap = integrator_gate_history_entry_count_caption(_ig_hist)
            if _ig_hist_count_cap:
                st.caption(_ig_hist_count_cap)
            _ig_hist_fail_cap = integrator_gate_history_failure_reason_caption(
                _ig_hist,
            )
            if _ig_hist_fail_cap:
                st.caption(_ig_hist_fail_cap)
            st.dataframe(_ig_hist_rows, use_container_width=True)
            _ig_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ig_hist_slug = integrator_gate_history_export_filename_slug(
                run_id.strip(),
            )
            _ig_hist_csv = integrator_gate_history_table_rows_csv(_ig_hist_rows)
            _ig_hist_json = integrator_gate_history_export_json(_ig_hist)
            _ig_dl_col, _ig_dl_json_col = st.columns(2)
            with _ig_dl_col:
                st.download_button(
                    label="Download integrator gate history CSV",
                    data=_ig_hist_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_integrator_gate_history_{_ig_hist_slug}_{_ig_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_integrator_gate_history_csv",
                )
            with _ig_dl_json_col:
                st.download_button(
                    label="Download integrator gate history JSON",
                    data=_ig_hist_json.encode("utf-8"),
                    file_name=(
                        f"hermes_integrator_gate_history_{_ig_hist_slug}_{_ig_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_integrator_gate_history_json",
                )
            _ig_hist_metrics = integrator_gate_history_operator_metrics(_ig_hist)
            _ig_hist_metrics_cap = integrator_gate_history_operator_metrics_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_metrics_cap:
                st.caption(_ig_hist_metrics_cap)
            _ig_hist_verdict_cap = integrator_gate_history_verdict_tally_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_verdict_cap:
                st.caption(_ig_hist_verdict_cap)
            _ig_hist_bundles_cap = integrator_gate_history_distinct_bundles_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_bundles_cap:
                st.caption(_ig_hist_bundles_cap)
            _ig_hist_score_cap = integrator_gate_history_score_range_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_score_cap:
                st.caption(_ig_hist_score_cap)
            _ig_hist_margin_cap = integrator_gate_history_latest_margin_caption(
                _ig_hist_metrics,
            )
            if _ig_hist_margin_cap:
                st.caption(_ig_hist_margin_cap)
            _ig_hist_metric_rows = integrator_gate_history_metrics_table_rows(
                _ig_hist_metrics,
            )
            st.caption(
                "Operator metrics over the **same** bounded history. "
                "**Latest score minus min pass** is "
                "``integrator_score - min_score_to_pass`` on the latest row only; "
                "verdict may still reflect other rules."
            )
            st.dataframe(
                _ig_hist_metric_rows,
                use_container_width=True,
                hide_index=True,
            )
            if _ig_hist_metric_rows:
                _ig_hist_metrics_json = (
                    integrator_gate_history_operator_metrics_export_json(
                        _ig_hist_metrics,
                    )
                )
                _ig_hist_metrics_csv = (
                    integrator_gate_history_operator_metrics_table_rows_csv(
                        _ig_hist_metric_rows,
                    )
                )
                _ig_hist_metrics_dl_json_col, _ig_hist_metrics_dl_csv_col = (
                    st.columns(2)
                )
                with _ig_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download integrator gate history "
                            "operator metrics JSON"
                        ),
                        data=_ig_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_integrator_gate_history_operator_metrics_"
                            f"{_ig_hist_slug}_{_ig_hist_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_integrator_gate_history_operator_metrics_json",
                    )
                with _ig_hist_metrics_dl_csv_col:
                    if _ig_hist_metrics_csv:
                        st.download_button(
                            label=(
                            "Download integrator gate history "
                            "operator metrics CSV"
                        ),
                            data=_ig_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_integrator_gate_history_operator_metrics_"
                                f"{_ig_hist_slug}_{_ig_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_integrator_gate_history_operator_metrics_csv",
                        )
            with st.expander(
                "Raw integrator_gate_history operator metrics JSON",
                expanded=False,
            ):
                st.json(_ig_hist_metrics)
            with st.expander("Raw integrator_gate_history JSON", expanded=False):
                st.json(_ig_hist)
    _ig_delta = integrator_gate_delta_from_timeline(data)
    _ig_delta_rows = integrator_gate_delta_summary_rows(_ig_delta)
