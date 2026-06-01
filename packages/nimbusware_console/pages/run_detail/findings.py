from __future__ import annotations

import streamlit as st

from nimbusware_client.http import HTTPError
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.pages.run_detail._imports_common import datetime, st, timezone
from nimbusware_console.pages.run_detail._imports_display_a import (
    findings_empty_caption,
    findings_export_filename_slug,
    findings_export_json,
    findings_list_from_response,
    findings_operator_metrics,
    findings_operator_metrics_caption,
    findings_operator_metrics_export_json,
    findings_operator_metrics_table_rows,
    findings_operator_metrics_table_rows_csv,
    findings_table_rows,
    findings_table_rows_csv,
)
from nimbusware_console.services import runs as runs_svc


def render_run_detail_findings(run_id: str) -> None:
    if st.button("Load findings") and run_id.strip():
        try:
            _find_body = runs_svc.fetch_findings(run_id)
            st.subheader("Findings")
            _find_list = findings_list_from_response(_find_body)
            if not _find_list:
                st.caption(findings_empty_caption())
            else:
                _find_metrics = findings_operator_metrics(_find_list)
                _find_metrics_cap = findings_operator_metrics_caption(_find_metrics)
                if _find_metrics_cap:
                    st.caption(_find_metrics_cap)
                _find_metric_rows = findings_operator_metrics_table_rows(
                    _find_metrics,
                )
                _find_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _find_slug = findings_export_filename_slug(run_id.strip())
                if _find_metric_rows:
                    st.dataframe(
                        _find_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _find_metrics_json = findings_operator_metrics_export_json(
                        _find_metrics,
                    )
                    _find_metrics_csv = findings_operator_metrics_table_rows_csv(
                        _find_metric_rows,
                    )
                    (
                        _find_metrics_dl_json_col,
                        _find_metrics_dl_csv_col,
                    ) = st.columns(2)
                    with _find_metrics_dl_json_col:
                        st.download_button(
                            label="Download findings operator metrics JSON",
                            data=_find_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_findings_operator_metrics_"
                                f"{_find_slug}_{_find_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_findings_operator_metrics_json",
                        )
                    with _find_metrics_dl_csv_col:
                        if _find_metrics_csv:
                            st.download_button(
                                label="Download findings operator metrics CSV",
                                data=_find_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_findings_operator_metrics_"
                                    f"{_find_slug}_{_find_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_findings_operator_metrics_csv",
                            )
                _find_table_rows = findings_table_rows(_find_list)
                st.dataframe(
                    _find_table_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _find_json = findings_export_json(_find_body)
                _find_csv = findings_table_rows_csv(_find_table_rows)
                _find_dl_json_col, _find_dl_csv_col = st.columns(2)
                with _find_dl_json_col:
                    st.download_button(
                        label="Download findings JSON",
                        data=_find_json.encode("utf-8"),
                        file_name=(
                            f"hermes_findings_{_find_slug}_{_find_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_findings_json",
                    )
                with _find_dl_csv_col:
                    if _find_csv:
                        st.download_button(
                            label="Download findings CSV",
                            data=_find_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_findings_{_find_slug}_{_find_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_findings_csv",
                        )
            with st.expander("Raw findings JSON", expanded=False):
                st.json(_find_body)
        except HTTPError as exc:
            render_api_error(exc)
