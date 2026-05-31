from __future__ import annotations

from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    Path,
    datetime,
    os,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
    run_escalated_actor_without_notes_caption,
    run_escalated_delta_export_filename_slug,
    run_escalated_delta_export_json,
    run_escalated_delta_from_timeline,
    run_escalated_delta_operator_metrics,
    run_escalated_delta_operator_metrics_caption,
    run_escalated_delta_operator_metrics_export_json,
    run_escalated_delta_operator_metrics_table_rows,
    run_escalated_delta_operator_metrics_table_rows_csv,
    run_escalated_delta_summary_rows,
    run_escalated_delta_table_rows_csv,
    run_escalated_delta_transition_caption,
    run_escalated_event_id_caption,
    run_escalated_export_filename_slug,
    run_escalated_export_json,
    run_escalated_from_timeline,
    run_escalated_history_distinct_actors_caption,
    run_escalated_history_entry_count_caption,
    run_escalated_history_export_filename_slug,
    run_escalated_history_export_json,
    run_escalated_history_from_timeline,
    run_escalated_history_operator_metrics,
    run_escalated_history_operator_metrics_caption,
    run_escalated_history_operator_metrics_export_json,
    run_escalated_history_operator_metrics_table_rows,
    run_escalated_history_operator_metrics_table_rows_csv,
    run_escalated_history_table_rows,
    run_escalated_history_table_rows_csv,
    run_escalated_notes_preview_caption,
    run_escalated_occurred_at_caption,
    run_escalated_operator_metrics,
    run_escalated_operator_metrics_caption,
    run_escalated_operator_metrics_export_json,
    run_escalated_operator_metrics_table_rows,
    run_escalated_operator_metrics_table_rows_csv,
    run_escalated_policy_cross_ref_caption,
    run_escalated_reason_summary_caption,
    run_escalated_summary_rows,
    run_escalated_summary_rows_csv,
    self_refinement_marker_history_entry_count_caption,
    self_refinement_marker_history_export_filename_slug,
    self_refinement_marker_history_export_json,
    self_refinement_marker_history_from_timeline,
    self_refinement_marker_history_operator_metrics,
    self_refinement_marker_history_operator_metrics_caption,
    self_refinement_marker_history_operator_metrics_export_json,
    self_refinement_marker_history_operator_metrics_table_rows,
    self_refinement_marker_history_operator_metrics_table_rows_csv,
    self_refinement_marker_history_table_rows,
    self_refinement_marker_history_table_rows_csv,
)



def _render_self_refinement_marker_history(run_id: str, data: dict) -> None:
    _sr_marker_hist = self_refinement_marker_history_from_timeline(data)
    _sr_marker_hist_rows = self_refinement_marker_history_table_rows(
        _sr_marker_hist,
    )
    with st.expander(
        "Self-refinement marker history (from timeline)",
        expanded=False,
    ):
        if not _sr_marker_hist_rows:
            st.caption(
                "No ``self_refinement_marker_history`` on this timeline "
                "(no self_refinement:policy stage.started markers yet)."
            )
        else:
            st.caption(
                "Chronological policy markers (bounded on the API; latest "
                "summary matches **Self-refinement** above)."
            )
            _sr_marker_hist_cap = (
                self_refinement_marker_history_entry_count_caption(
                    _sr_marker_hist,
                )
            )
            if _sr_marker_hist_cap:
                st.caption(_sr_marker_hist_cap)
            _sr_marker_hist_metrics = (
                self_refinement_marker_history_operator_metrics(
                    _sr_marker_hist,
                )
            )
            _sr_marker_hist_metrics_cap = (
                self_refinement_marker_history_operator_metrics_caption(
                    _sr_marker_hist_metrics,
                )
            )
            if _sr_marker_hist_metrics_cap:
                st.caption(_sr_marker_hist_metrics_cap)
            _sr_marker_hist_metric_rows = (
                self_refinement_marker_history_operator_metrics_table_rows(
                    _sr_marker_hist_metrics,
                )
            )
            _sr_marker_hist_ts = datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ",
            )
            _sr_marker_hist_slug = (
                self_refinement_marker_history_export_filename_slug(
                    run_id.strip(),
                )
            )
            if _sr_marker_hist_metric_rows:
                st.dataframe(
                    _sr_marker_hist_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _sr_marker_hist_metrics_json = (
                    self_refinement_marker_history_operator_metrics_export_json(
                        _sr_marker_hist_metrics,
                    )
                )
                _sr_marker_hist_metrics_csv = (
                    self_refinement_marker_history_operator_metrics_table_rows_csv(
                        _sr_marker_hist_metric_rows,
                    )
                )
                (
                    _sr_marker_hist_metrics_dl_json_col,
                    _sr_marker_hist_metrics_dl_csv_col,
                ) = st.columns(2)
                with _sr_marker_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download self-refinement marker history "
                            "operator metrics JSON"
                        ),
                        data=_sr_marker_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_self_refinement_marker_history_operator_metrics_"
                            f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_self_refinement_marker_history_"
                            "operator_metrics_json"
                        ),
                    )
                with _sr_marker_hist_metrics_dl_csv_col:
                    if _sr_marker_hist_metrics_csv:
                        st.download_button(
                            label=(
                                "Download self-refinement marker history "
                                "operator metrics CSV"
                            ),
                            data=_sr_marker_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_self_refinement_marker_history_operator_metrics_"
                                f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_self_refinement_marker_history_"
                                "operator_metrics_csv"
                            ),
                        )
            st.dataframe(_sr_marker_hist_rows, use_container_width=True)
            _sr_marker_hist_csv = self_refinement_marker_history_table_rows_csv(
                _sr_marker_hist_rows,
            )
            _sr_marker_hist_json = self_refinement_marker_history_export_json(
                _sr_marker_hist,
            )
            _sr_marker_dl_col, _sr_marker_dl_json_col = st.columns(2)
            with _sr_marker_dl_col:
                st.download_button(
                    label="Download marker history CSV",
                    data=_sr_marker_hist_csv.encode("utf-8"),
                    file_name=(
                        "hermes_self_refinement_marker_history_"
                        f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_self_refinement_marker_history_csv",
                )
            with _sr_marker_dl_json_col:
                st.download_button(
                    label="Download marker history JSON",
                    data=_sr_marker_hist_json.encode("utf-8"),
                    file_name=(
                        "hermes_self_refinement_marker_history_"
                        f"{_sr_marker_hist_slug}_{_sr_marker_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_self_refinement_marker_history_json",
                )
            with st.expander(
                "Raw self_refinement_marker_history JSON",
                expanded=False,
            ):
                st.json(_sr_marker_hist)
    _re = run_escalated_from_timeline(data)
    _re_rows = run_escalated_summary_rows(_re)
