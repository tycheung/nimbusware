from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import datetime, st, timezone
from nimbusware_console.pages.run_detail._imports_display_a import (
    critic_matrix_export_filename_slug,
    critic_matrix_export_json,
    critic_matrix_operator_metrics,
    critic_matrix_operator_metrics_caption,
    critic_matrix_operator_metrics_export_json,
    critic_matrix_operator_metrics_table_rows,
    critic_matrix_operator_metrics_table_rows_csv,
    critic_matrix_rows_from_events,
    critic_matrix_table_rows_csv,
)


def render_run_detail_critic_matrix(run_id: str, events: list) -> None:
    _crit_rows = critic_matrix_rows_from_events(events)
    st.subheader("Critic matrix (extracted)")
    if not _crit_rows:
        st.dataframe([{"note": "no critic.verdict.emitted events"}])
    else:
        _crit_metrics = critic_matrix_operator_metrics(_crit_rows)
        _crit_cap = critic_matrix_operator_metrics_caption(_crit_metrics)
        if _crit_cap:
            st.caption(_crit_cap)
        _crit_metric_rows = critic_matrix_operator_metrics_table_rows(
            _crit_metrics,
        )
        _crit_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _crit_slug = critic_matrix_export_filename_slug(run_id.strip())
        if _crit_metric_rows:
            st.dataframe(
                _crit_metric_rows,
                use_container_width=True,
                hide_index=True,
            )
            _crit_metrics_json = critic_matrix_operator_metrics_export_json(
                _crit_metrics,
            )
            _crit_metrics_csv = critic_matrix_operator_metrics_table_rows_csv(
                _crit_metric_rows,
            )
            (
                _crit_metrics_dl_json_col,
                _crit_metrics_dl_csv_col,
            ) = st.columns(2)
            with _crit_metrics_dl_json_col:
                st.download_button(
                    label="Download critic matrix operator metrics JSON",
                    data=_crit_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_critic_matrix_operator_metrics_{_crit_slug}_{_crit_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_critic_matrix_operator_metrics_json",
                )
            with _crit_metrics_dl_csv_col:
                if _crit_metrics_csv:
                    st.download_button(
                        label=("Download critic matrix operator metrics CSV"),
                        data=_crit_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_critic_matrix_operator_metrics_{_crit_slug}_{_crit_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critic_matrix_operator_metrics_csv",
                    )
        st.dataframe(_crit_rows, use_container_width=True, hide_index=True)
        _crit_json = critic_matrix_export_json(_crit_rows)
        _crit_csv = critic_matrix_table_rows_csv(_crit_rows)
        _crit_dl_json_col, _crit_dl_csv_col = st.columns(2)
        with _crit_dl_json_col:
            st.download_button(
                label="Download critic matrix JSON",
                data=_crit_json.encode("utf-8"),
                file_name=(f"hermes_critic_matrix_{_crit_slug}_{_crit_ts}.json"),
                mime="application/json",
                key="hermes_dl_critic_matrix_json",
            )
        with _crit_dl_csv_col:
            if _crit_csv:
                st.download_button(
                    label="Download critic matrix CSV",
                    data=_crit_csv.encode("utf-8"),
                    file_name=(f"hermes_critic_matrix_{_crit_slug}_{_crit_ts}.csv"),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_critic_matrix_csv",
                )
