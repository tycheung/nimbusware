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



def _render_run_escalated(run_id: str, data: dict) -> None:
    with st.expander("Run escalated (from timeline)", expanded=False):
        if not _re_rows:
            st.caption(
                "No run_escalated summary on this timeline (no run.escalated "
                "events yet)."
            )
        else:
            st.caption(
                "Latest run.escalated summary (same top-level run_escalated as "
                "GET …/timeline)."
            )
            st.dataframe(_re_rows, use_container_width=True)
            _re_reason_cap = run_escalated_reason_summary_caption(_re)
            if _re_reason_cap:
                st.caption(_re_reason_cap)
            _re_at_cap = run_escalated_occurred_at_caption(_re)
            if _re_at_cap:
                st.caption(_re_at_cap)
            _re_event_cap = run_escalated_event_id_caption(_re)
            if _re_event_cap:
                st.caption(_re_event_cap)
            _re_notes_cap = run_escalated_notes_preview_caption(_re)
            if _re_notes_cap:
                st.caption(_re_notes_cap)
            _re_root = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
            _re_cap = run_escalated_policy_cross_ref_caption(_re_root, _re)
            if _re_cap:
                st.caption(_re_cap)
            _re_actor_notes = run_escalated_actor_without_notes_caption(_re)
            if _re_actor_notes:
                st.caption(_re_actor_notes)
            _re_metrics = run_escalated_operator_metrics(_re)
            _re_metrics_cap = run_escalated_operator_metrics_caption(
                _re_metrics,
            )
            if _re_metrics_cap:
                st.caption(_re_metrics_cap)
            _re_metric_rows = run_escalated_operator_metrics_table_rows(
                _re_metrics,
            )
            _re_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _re_slug = run_escalated_export_filename_slug(run_id.strip())
            if _re_metric_rows:
                st.dataframe(
                    _re_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _re_metrics_json = run_escalated_operator_metrics_export_json(
                    _re_metrics,
                )
                _re_metrics_csv = (
                    run_escalated_operator_metrics_table_rows_csv(
                        _re_metric_rows,
                    )
                )
                _re_metrics_dl_json_col, _re_metrics_dl_csv_col = st.columns(2)
                with _re_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download run escalated operator "
                            "metrics JSON"
                        ),
                        data=_re_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_operator_metrics_"
                            f"{_re_slug}_{_re_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_run_escalated_operator_metrics_json",
                    )
                with _re_metrics_dl_csv_col:
                    if _re_metrics_csv:
                        st.download_button(
                            label=(
                                "Download run escalated operator "
                                "metrics CSV"
                            ),
                            data=_re_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_run_escalated_operator_metrics_"
                                f"{_re_slug}_{_re_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_run_escalated_operator_metrics_csv",
                        )
            _re_sum_csv = run_escalated_summary_rows_csv(_re_rows)
            _re_sum_json = run_escalated_export_json(_re)
            _re_sum_dl_col, _re_sum_dl_json_col = st.columns(2)
            with _re_sum_dl_col:
                if _re_sum_csv:
                    st.download_button(
                        label="Download run escalated summary CSV",
                        data=_re_sum_csv.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_summary_"
                            f"{_re_slug}_{_re_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_run_escalated_summary_csv",
                    )
            with _re_sum_dl_json_col:
                st.download_button(
                    label="Download run escalated summary JSON",
                    data=_re_sum_json.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_summary_"
                        f"{_re_slug}_{_re_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_escalated_summary_json",
                )
            with st.expander("Raw run_escalated JSON", expanded=False):
                st.json(_re)
    _re_hist = run_escalated_history_from_timeline(data)
    _re_hist_rows = run_escalated_history_table_rows(_re_hist)
