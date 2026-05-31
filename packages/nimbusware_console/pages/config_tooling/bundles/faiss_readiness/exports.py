from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def render_faiss_exports_panel(
    repo_root: Path,
    *,
    _faiss: dict[str, Any],
    _faiss_sum: dict[str, Any],
) -> None:
        _faiss_sum_metrics = bundle_faiss_readiness_summary_operator_metrics(_faiss_sum)
        _faiss_sum_metrics_cap = bundle_faiss_readiness_summary_operator_metrics_caption(
            _faiss_sum_metrics,
        )
        if _faiss_sum_metrics_cap:
            st.caption(_faiss_sum_metrics_cap)
        _faiss_sum_metric_rows = bundle_faiss_readiness_summary_operator_metrics_table_rows(
            _faiss_sum_metrics,
        )
        if _faiss_sum_metric_rows:
            st.dataframe(_faiss_sum_metric_rows, use_container_width=True)
        _faiss_ready_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _faiss_ready_metrics_slug = (
            bundle_faiss_readiness_summary_operator_metrics_export_filename_slug()
        )
        _faiss_ready_metrics_json = (
            bundle_faiss_readiness_summary_operator_metrics_export_json(_faiss_sum_metrics)
        )
        _faiss_ready_metrics_csv = (
            bundle_faiss_readiness_summary_operator_metrics_table_rows_csv(
                _faiss_sum_metric_rows,
            )
        )
        _faiss_ready_m_dl_json_col, _faiss_ready_m_dl_csv_col = st.columns(2)
        with _faiss_ready_m_dl_json_col:
            st.download_button(
                label="Download FAISS readiness operator metrics JSON",
                data=_faiss_ready_metrics_json.encode("utf-8"),
                file_name=(
                    f"hermes_{_faiss_ready_metrics_slug}_"
                    f"{bundle_faiss_readiness_export_filename_slug(repo_root)}_"
                    f"{_faiss_ready_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_faiss_readiness_metrics_json",
            )
        with _faiss_ready_m_dl_csv_col:
            if _faiss_ready_metrics_csv:
                st.download_button(
                    label="Download FAISS readiness operator metrics CSV",
                    data=_faiss_ready_metrics_csv.encode("utf-8"),
                    file_name=(
                        f"hermes_{_faiss_ready_metrics_slug}_"
                        f"{bundle_faiss_readiness_export_filename_slug(repo_root)}_"
                        f"{_faiss_ready_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_faiss_readiness_metrics_csv",
                )
        _faiss_ready_slug = bundle_faiss_readiness_export_filename_slug(repo_root)
        _faiss_ready_json = bundle_faiss_readiness_summary_export_json(repo_root)
        _faiss_ready_rows = bundle_faiss_readiness_summary_table_rows(_faiss_sum)
        _faiss_ready_csv = bundle_faiss_readiness_summary_table_rows_csv(_faiss_ready_rows)
        _faiss_ready_dl_json_col, _faiss_ready_dl_csv_col = st.columns(2)
        with _faiss_ready_dl_json_col:
            st.download_button(
                label="Download FAISS index readiness JSON",
                data=_faiss_ready_json.encode("utf-8"),
                file_name=(
                    "hermes_bundle_faiss_readiness_"
                    f"{_faiss_ready_slug}_{_faiss_ready_ts}.json"
                ),
                mime="application/json",
                key="hermes_dl_bundle_faiss_readiness_json",
            )
        with _faiss_ready_dl_csv_col:
            if _faiss_ready_csv:
                st.download_button(
                    label="Download FAISS index readiness CSV",
                    data=_faiss_ready_csv.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_readiness_"
                        f"{_faiss_ready_slug}_{_faiss_ready_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_faiss_readiness_csv",
                )
        _faiss_status_rows = bundle_faiss_index_status_table_rows(_faiss)
        if _faiss_status_rows:
            _faiss_status_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _faiss_status_slug = bundle_faiss_readiness_export_filename_slug(repo_root)
            _faiss_status_json = bundle_faiss_index_status_export_json(_faiss)
            _faiss_status_csv = bundle_faiss_index_status_table_rows_csv(_faiss_status_rows)
            _faiss_status_dl_json_col, _faiss_status_dl_csv_col = st.columns(2)
            with _faiss_status_dl_json_col:
                st.download_button(
                    label="Download FAISS index sync status JSON",
                    data=_faiss_status_json.encode("utf-8"),
                    file_name=(
                        "hermes_bundle_faiss_index_status_"
                        f"{_faiss_status_slug}_{_faiss_status_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_bundle_faiss_index_status_json",
                )
            with _faiss_status_dl_csv_col:
                if _faiss_status_csv:
                    st.download_button(
                        label="Download FAISS index sync status CSV",
                        data=_faiss_status_csv.encode("utf-8"),
                        file_name=(
                            "hermes_bundle_faiss_index_status_"
                            f"{_faiss_status_slug}_{_faiss_status_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_faiss_index_status_csv",
                    )
        with st.expander("Raw index readiness JSON", expanded=False):
            st.json(_faiss)
