from __future__ import annotations

import os
from pathlib import Path
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
    preflight_history_from_timeline,
    scraper_fetch_artifacts_caption,
    scraper_fetch_failure_reason_caption,
    scraper_fetch_fetches_export_filename_slug,
    scraper_fetch_fetches_export_json,
    scraper_fetch_fetches_table_rows,
    scraper_fetch_fetches_table_rows_csv,
    scraper_fetch_operator_metrics,
    scraper_fetch_operator_metrics_caption,
    scraper_fetch_operator_metrics_export_json,
    scraper_fetch_operator_metrics_table_rows,
    scraper_fetch_operator_metrics_table_rows_csv,
    scraper_fetch_outcome_caption,
    scraper_fetch_summary_export_filename_slug,
    scraper_fetch_summary_export_json,
    scraper_fetch_summary_rows_csv,
)


def _render_timeline_misc_scraper(run_id: str, data: dict, _wf_pick: str) -> None:
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    with st.expander("Scraper fetch (from timeline)", expanded=False):
        if not _sf_rows:
            st.caption(
                "No scraper_fetch summary on this timeline (no terminal "
                "scraper:fetch stage.passed / stage.failed yet)."
            )
        else:
            st.caption(
                "Latest scraper:fetch terminal stage summary (same top-level "
                "scraper_fetch as GET …/timeline)."
            )
            _sf_outcome_cap = scraper_fetch_outcome_caption(_sf)
            if _sf_outcome_cap:
                st.caption(_sf_outcome_cap)
            _sf_fail_cap = scraper_fetch_failure_reason_caption(_sf)
            if _sf_fail_cap:
                st.caption(_sf_fail_cap)
            _sf_metrics = scraper_fetch_operator_metrics(_sf)
            _sf_metrics_cap = scraper_fetch_operator_metrics_caption(_sf_metrics)
            if _sf_metrics_cap:
                st.caption(_sf_metrics_cap)
            _sf_metric_rows = scraper_fetch_operator_metrics_table_rows(
                _sf_metrics,
            )
            _sf_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sf_sum_slug = scraper_fetch_summary_export_filename_slug(
                run_id.strip(),
            )
            if _sf_metric_rows:
                st.dataframe(
                    _sf_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _sf_metrics_json = scraper_fetch_operator_metrics_export_json(
                    _sf_metrics,
                )
                _sf_metrics_csv = scraper_fetch_operator_metrics_table_rows_csv(
                    _sf_metric_rows,
                )
                _sf_metrics_dl_json_col, _sf_metrics_dl_csv_col = st.columns(2)
                with _sf_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download scraper fetch operator "
                            "metrics JSON"
                        ),
                        data=_sf_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_scraper_fetch_operator_metrics_"
                            f"{_sf_sum_slug}_{_sf_sum_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_scraper_fetch_operator_metrics_json",
                    )
                with _sf_metrics_dl_csv_col:
                    if _sf_metrics_csv:
                        st.download_button(
                            label=(
                                "Download scraper fetch operator "
                                "metrics CSV"
                            ),
                            data=_sf_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_scraper_fetch_operator_metrics_"
                                f"{_sf_sum_slug}_{_sf_sum_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_scraper_fetch_operator_metrics_csv",
                        )
            st.dataframe(_sf_rows, use_container_width=True)
            _sf_fetch_rows = scraper_fetch_fetches_table_rows(_sf)
            if _sf_fetch_rows:
                st.caption("Per-URL fetches (from timeline ``scraper_fetch.fetches``)")
                _sf_artifacts_cap = scraper_fetch_artifacts_caption(_sf)
                if _sf_artifacts_cap:
                    st.caption(_sf_artifacts_cap)
                st.dataframe(_sf_fetch_rows, use_container_width=True)
                _sf_fetch_ts = datetime.now(timezone.utc).strftime(
                    "%Y%m%dT%H%M%SZ",
                )
                _sf_fetch_slug = scraper_fetch_fetches_export_filename_slug(
                    run_id.strip(),
                )
                _sf_fetch_csv = scraper_fetch_fetches_table_rows_csv(
                    _sf_fetch_rows,
                )
                _sf_fetch_json = scraper_fetch_fetches_export_json(_sf)
                _sf_fetch_dl_col, _sf_fetch_dl_json_col = st.columns(2)
                with _sf_fetch_dl_col:
                    st.download_button(
                        label="Download scraper fetches CSV",
                        data=_sf_fetch_csv.encode("utf-8"),
                        file_name=(
                            "hermes_scraper_fetch_fetches_"
                            f"{_sf_fetch_slug}_{_sf_fetch_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_scraper_fetch_fetches_csv",
                    )
                with _sf_fetch_dl_json_col:
                    st.download_button(
                        label="Download scraper fetches JSON",
                        data=_sf_fetch_json.encode("utf-8"),
                        file_name=(
                            "hermes_scraper_fetch_fetches_"
                            f"{_sf_fetch_slug}_{_sf_fetch_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_scraper_fetch_fetches_json",
                    )
            _sf_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sf_sum_slug = scraper_fetch_summary_export_filename_slug(
                run_id.strip(),
            )
            _sf_sum_csv = scraper_fetch_summary_rows_csv(_sf_rows)
            _sf_sum_json = scraper_fetch_summary_export_json(_sf)
            _sf_sum_dl_col, _sf_sum_dl_json_col = st.columns(2)
            with _sf_sum_dl_col:
                st.download_button(
                    label="Download scraper fetch summary CSV",
                    data=_sf_sum_csv.encode("utf-8"),
                    file_name=(
                        "hermes_scraper_fetch_summary_"
                        f"{_sf_sum_slug}_{_sf_sum_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_scraper_fetch_summary_csv",
                )
            with _sf_sum_dl_json_col:
                st.download_button(
                    label="Download scraper fetch summary JSON",
                    data=_sf_sum_json.encode("utf-8"),
                    file_name=(
                        "hermes_scraper_fetch_summary_"
                        f"{_sf_sum_slug}_{_sf_sum_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_scraper_fetch_summary_json",
                )
            with st.expander("Raw scraper_fetch JSON", expanded=False):
                st.json(_sf)
    _pf = preflight_history_from_timeline(data)
