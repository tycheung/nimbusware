from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    datetime,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
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
)


def _render_run_escalated_delta(run_id: str, data: dict) -> None:
    _re_delta = run_escalated_delta_from_timeline(data)
    with st.expander("Run escalated delta (latest vs prior)", expanded=False):
        if not _re_delta:
            st.caption(
                "No ``run_escalated_delta`` — need at least two "
                "run.escalated events on this timeline."
            )
        else:
            st.caption(
                "Diff between the last two ``run.escalated`` events "
                "(same field as GET …/timeline ``run_escalated_delta``)."
            )
            _re_delta_cap = run_escalated_delta_transition_caption(_re_delta)
            if _re_delta_cap:
                st.caption(_re_delta_cap)
            _re_delta_metrics = run_escalated_delta_operator_metrics(_re_delta)
            _re_delta_metrics_cap = run_escalated_delta_operator_metrics_caption(
                _re_delta_metrics,
            )
            if _re_delta_metrics_cap:
                st.caption(_re_delta_metrics_cap)
            _re_delta_metric_rows = run_escalated_delta_operator_metrics_table_rows(
                _re_delta_metrics,
            )
            _re_delta_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _re_delta_slug = run_escalated_delta_export_filename_slug(
                run_id.strip(),
            )
            if _re_delta_metric_rows:
                st.dataframe(
                    _re_delta_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _re_delta_metrics_json = (
                    run_escalated_delta_operator_metrics_export_json(
                        _re_delta_metrics,
                    )
                )
                _re_delta_metrics_csv = (
                    run_escalated_delta_operator_metrics_table_rows_csv(
                        _re_delta_metric_rows,
                    )
                )
                (
                    _re_delta_metrics_dl_json_col,
                    _re_delta_metrics_dl_csv_col,
                ) = st.columns(2)
                with _re_delta_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download run escalated delta operator "
                            "metrics JSON"
                        ),
                        data=_re_delta_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_run_escalated_delta_operator_metrics_"
                            f"{_re_delta_slug}_{_re_delta_ts}.json"
                        ),
                        mime="application/json",
                        key=(
                            "hermes_dl_run_escalated_delta_operator_"
                            "metrics_json"
                        ),
                    )
                with _re_delta_metrics_dl_csv_col:
                    if _re_delta_metrics_csv:
                        st.download_button(
                            label=(
                                "Download run escalated delta operator "
                                "metrics CSV"
                            ),
                            data=_re_delta_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_run_escalated_delta_operator_metrics_"
                                f"{_re_delta_slug}_{_re_delta_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=(
                                "hermes_dl_run_escalated_delta_operator_"
                                "metrics_csv"
                            ),
                        )
            _re_delta_sum_rows = run_escalated_delta_summary_rows(_re_delta)
            _re_delta_csv = run_escalated_delta_table_rows_csv(_re_delta_sum_rows)
            _re_delta_json = run_escalated_delta_export_json(_re_delta)
            _re_delta_dl_col, _re_delta_dl_json_col = st.columns(2)
            with _re_delta_dl_col:
                st.download_button(
                    label="Download run escalated delta CSV",
                    data=_re_delta_csv.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_delta_"
                        f"{_re_delta_slug}_{_re_delta_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_run_escalated_delta_csv",
                )
            with _re_delta_dl_json_col:
                st.download_button(
                    label="Download run escalated delta JSON",
                    data=_re_delta_json.encode("utf-8"),
                    file_name=(
                        "hermes_run_escalated_delta_"
                        f"{_re_delta_slug}_{_re_delta_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_run_escalated_delta_json",
                )
            with st.expander("Raw run_escalated_delta JSON", expanded=False):
                st.json(_re_delta)
