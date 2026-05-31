from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    datetime,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
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
)


def _render_run_escalated_history(run_id: str, data: dict) -> None:
    _re_hist = run_escalated_history_from_timeline(data)
    _re_hist_rows = run_escalated_history_table_rows(_re_hist)
    with st.expander("Run escalated history (from timeline)", expanded=False):
        if not _re_hist_rows:
            st.caption(
                "No ``run_escalated_history`` on this timeline (no "
                "run.escalated events recorded)."
            )
        else:
            st.caption(
                "Chronological ``run.escalated`` rows (bounded on the API; "
                "latest row matches **Run escalated** summary)."
            )
            _re_hist_count_cap = run_escalated_history_entry_count_caption(
                _re_hist,
            )
            if _re_hist_count_cap:
                st.caption(_re_hist_count_cap)
            _re_hist_metrics = run_escalated_history_operator_metrics(_re_hist)
            _re_hist_metrics_cap = run_escalated_history_operator_metrics_caption(
                _re_hist_metrics,
            )
            if _re_hist_metrics_cap:
                st.caption(_re_hist_metrics_cap)
            _re_hist_actors_cap = run_escalated_history_distinct_actors_caption(
                _re_hist_metrics,
            )
            if _re_hist_actors_cap:
                st.caption(_re_hist_actors_cap)
            _re_hist_metric_rows = run_escalated_history_operator_metrics_table_rows(
                _re_hist_metrics,
            )
            _re_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _re_hist_slug = run_escalated_history_export_filename_slug(
                run_id.strip(),
            )
            if _re_hist_metric_rows:
                st.dataframe(
                    _re_hist_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _re_hist_metrics_json = (
                    run_escalated_history_operator_metrics_export_json(
                        _re_hist_metrics,
                    )
                )
                _re_hist_metrics_csv = (
                    run_escalated_history_operator_metrics_table_rows_csv(
                        _re_hist_metric_rows,
                    )
                )
                (
                    _re_hist_metrics_dl_json_col,
                    _re_hist_metrics_dl_csv_col,
                ) = st.columns(2)
                with _re_hist_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download run escalated history operator "
                            "metrics JSON"
                        ),
                        data=_re_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_history_operator_metrics_"
                            f"{_re_hist_slug}_{_re_hist_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_run_escalated_history_operator_"
                            "metrics_json"
                        ),
                    )
                with _re_hist_metrics_dl_csv_col:
                    if _re_hist_metrics_csv:
                        st.download_button(
                            label=(
                                "Download run escalated history operator "
                                "metrics CSV"
                            ),
                            data=_re_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_run_escalated_history_operator_metrics_"
                                f"{_re_hist_slug}_{_re_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_run_escalated_history_operator_"
                                "metrics_csv"
                            ),
                        )
            st.dataframe(_re_hist_rows, use_container_width=True)
            _re_hist_csv = run_escalated_history_table_rows_csv(_re_hist_rows)
            _re_hist_json = run_escalated_history_export_json(_re_hist)
            _re_hist_dl_col, _re_hist_dl_json_col = st.columns(2)
            with _re_hist_dl_col:
                st.download_button(
                    label="Download run escalated history CSV",
                    data=_re_hist_csv.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_history_"
                        f"{_re_hist_slug}_{_re_hist_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_run_escalated_history_csv",
                )
            with _re_hist_dl_json_col:
                st.download_button(
                    label="Download run escalated history JSON",
                    data=_re_hist_json.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_history_"
                        f"{_re_hist_slug}_{_re_hist_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_escalated_history_json",
                )
            with st.expander("Raw run_escalated_history JSON", expanded=False):
                st.json(_re_hist)
