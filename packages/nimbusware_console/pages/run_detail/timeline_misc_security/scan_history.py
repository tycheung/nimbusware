from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    datetime,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
    security_scan_history_entry_count_caption,
    security_scan_history_export_filename_slug,
    security_scan_history_export_json,
    security_scan_history_from_timeline,
    security_scan_history_operator_metrics,
    security_scan_history_operator_metrics_caption,
    security_scan_history_operator_metrics_export_json,
    security_scan_history_operator_metrics_table_rows,
    security_scan_history_operator_metrics_table_rows_csv,
    security_scan_history_severity_sample_caption,
    security_scan_history_table_rows,
    security_scan_history_table_rows_csv,
)


def _render_security_scan_history(run_id: str, data: dict, _wf_pick: str) -> None:
    _ss_hist = security_scan_history_from_timeline(data)
    _ss_hist_rows = security_scan_history_table_rows(_ss_hist)
    with st.expander(
        "Security scan history (from timeline)",
        expanded=False,
    ):
        if not _ss_hist_rows:
            st.caption(
                "No ``security_scan_on_verify_history`` on this timeline "
                "(no finding.created with security_scan_* metadata yet)."
            )
        else:
            st.caption(
                "Chronological verifier scan findings (bounded on the API; "
                "latest row matches **Security scan on verify** summary)."
            )
            _ss_hist_cap = security_scan_history_entry_count_caption(_ss_hist)
            if _ss_hist_cap:
                st.caption(_ss_hist_cap)
            _ss_hist_metrics = security_scan_history_operator_metrics(_ss_hist)
            _ss_hist_metrics_cap = security_scan_history_operator_metrics_caption(
                _ss_hist_metrics,
            )
            if _ss_hist_metrics_cap:
                st.caption(_ss_hist_metrics_cap)
            _ss_hist_sev_cap = security_scan_history_severity_sample_caption(
                _ss_hist,
            )
            if _ss_hist_sev_cap:
                st.caption(_ss_hist_sev_cap)
            _ss_hist_metric_rows = security_scan_history_operator_metrics_table_rows(
                _ss_hist_metrics,
            )
            _ss_hist_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ss_hist_slug = security_scan_history_export_filename_slug(
                run_id.strip(),
            )
            if _ss_hist_metric_rows:
                st.dataframe(
                    _ss_hist_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _ss_hist_metrics_json = security_scan_history_operator_metrics_export_json(
                    _ss_hist_metrics,
                )
                _ss_hist_metrics_csv = security_scan_history_operator_metrics_table_rows_csv(
                    _ss_hist_metric_rows,
                )
                (
                    _ss_hist_metrics_dl_json_col,
                    _ss_hist_metrics_dl_csv_col,
                ) = st.columns(2)
                with _ss_hist_metrics_dl_json_col:
                    st.download_button(
                        label=("Download security scan history operator metrics JSON"),
                        data=_ss_hist_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_security_scan_history_operator_metrics_"
                            f"{_ss_hist_slug}_{_ss_hist_ts}.json"
                        ),
                        mime="application/json",
                        key=("hermes_dl_security_scan_history_operator_metrics_json"),
                    )
                with _ss_hist_metrics_dl_csv_col:
                    if _ss_hist_metrics_csv:
                        st.download_button(
                            label=("Download security scan history operator metrics CSV"),
                            data=_ss_hist_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_security_scan_history_operator_metrics_"
                                f"{_ss_hist_slug}_{_ss_hist_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key=("hermes_dl_security_scan_history_operator_metrics_csv"),
                        )
            st.dataframe(_ss_hist_rows, use_container_width=True)
            _ss_hist_csv = security_scan_history_table_rows_csv(_ss_hist_rows)
            _ss_hist_json = security_scan_history_export_json(_ss_hist)
            _ss_hist_dl_col, _ss_hist_dl_json_col = st.columns(2)
            with _ss_hist_dl_col:
                st.download_button(
                    label="Download security scan history CSV",
                    data=_ss_hist_csv.encode("utf-8"),
                    file_name=(f"hermes_security_scan_history_{_ss_hist_slug}_{_ss_hist_ts}.csv"),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_security_scan_history_csv",
                )
            with _ss_hist_dl_json_col:
                st.download_button(
                    label="Download security scan history JSON",
                    data=_ss_hist_json.encode("utf-8"),
                    file_name=(f"hermes_security_scan_history_{_ss_hist_slug}_{_ss_hist_ts}.json"),
                    mime="application/json",
                    key="hermes_dl_security_scan_history_json",
                )
            with st.expander(
                "Raw security_scan_on_verify_history JSON",
                expanded=False,
            ):
                st.json(_ss_hist)
