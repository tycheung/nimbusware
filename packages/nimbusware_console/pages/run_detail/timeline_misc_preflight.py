from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    Path,
    datetime,
    os,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
    preflight_history_checks_passed_caption,
    preflight_history_context_tokens_caption,
    preflight_history_event_id_caption,
    preflight_history_export_filename_slug,
    preflight_history_export_json,
    preflight_history_from_timeline,
    preflight_history_histogram_mode_caption,
    preflight_history_histogram_payload,
    preflight_history_latency_samples_table_rows,
    preflight_history_operator_metrics,
    preflight_history_operator_metrics_caption,
    preflight_history_operator_metrics_export_json,
    preflight_history_operator_metrics_table_rows,
    preflight_history_operator_metrics_table_rows_csv,
    preflight_history_p95_latency_caption,
    preflight_history_p95_source_caption,
    preflight_history_provider_caption,
    preflight_history_sample_count_caption,
    preflight_history_samples_table_caption,
    preflight_history_summary_rows,
    preflight_history_summary_rows_csv,
    preflight_history_validated_model_caption,
)


def _render_timeline_misc_preflight(run_id: str, data: dict, _wf_pick: str) -> None:
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    _pf = preflight_history_from_timeline(data)
    _pf_rows = preflight_history_summary_rows(_pf)
    with st.expander("Preflight history (from timeline)", expanded=False):
        if not _pf_rows:
            st.caption(
                "No preflight summary on this timeline (no "
                "model.preflight.passed yet, or skipped via "
                "HERMES_SKIP_PREFLIGHT)."
            )
        else:
            st.caption(
                "Latest model.preflight.passed summary (same top-level "
                "preflight as GET …/timeline). Histogram bucket edges: "
                "50 / 100 / 250 / 500 / 1000 / 2500 / 5000 / 10000 ms."
            )
            _pf_metrics = preflight_history_operator_metrics(_pf)
            _pf_metrics_cap = preflight_history_operator_metrics_caption(
                _pf_metrics,
            )
            if _pf_metrics_cap:
                st.caption(_pf_metrics_cap)
            _pf_metric_rows = preflight_history_operator_metrics_table_rows(
                _pf_metrics,
            )
            _pf_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pf_slug = preflight_history_export_filename_slug(run_id.strip())
            if _pf_metric_rows:
                st.dataframe(
                    _pf_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _pf_metrics_json = preflight_history_operator_metrics_export_json(
                    _pf_metrics,
                )
                _pf_metrics_csv = preflight_history_operator_metrics_table_rows_csv(
                    _pf_metric_rows,
                )
                _pf_metrics_dl_json_col, _pf_metrics_dl_csv_col = st.columns(2)
                with _pf_metrics_dl_json_col:
                    st.download_button(
                        label=(
                            "Download preflight history operator "
                            "metrics JSON"
                        ),
                        data=_pf_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_preflight_history_operator_metrics_"
                            f"{_pf_slug}_{_pf_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_preflight_history_operator_metrics_json",
                    )
                with _pf_metrics_dl_csv_col:
                    if _pf_metrics_csv:
                        st.download_button(
                            label=(
                                "Download preflight history operator "
                                "metrics CSV"
                            ),
                            data=_pf_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_preflight_history_operator_metrics_"
                                f"{_pf_slug}_{_pf_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_preflight_history_operator_metrics_csv",
                        )
            st.dataframe(_pf_rows, use_container_width=True)
            _pf_hist_mode_cap = preflight_history_histogram_mode_caption(_pf)
            if _pf_hist_mode_cap:
                st.caption(_pf_hist_mode_cap)
            _pf_samples_cap = preflight_history_samples_table_caption(_pf)
            if _pf_samples_cap:
                st.caption(_pf_samples_cap)
            _pf_sample_rows = preflight_history_latency_samples_table_rows(
                _pf,
            )
            if _pf_sample_rows:
                st.dataframe(_pf_sample_rows, use_container_width=True)
            _pf_p95_src_cap = preflight_history_p95_source_caption(_pf)
            if _pf_p95_src_cap:
                st.caption(_pf_p95_src_cap)
            _pf_p95_ms_cap = preflight_history_p95_latency_caption(_pf)
            if _pf_p95_ms_cap:
                st.caption(_pf_p95_ms_cap)
            _pf_event_cap = preflight_history_event_id_caption(_pf)
            if _pf_event_cap:
                st.caption(_pf_event_cap)
            _pf_checks_cap = preflight_history_checks_passed_caption(_pf)
            if _pf_checks_cap:
                st.caption(_pf_checks_cap)
            _pf_vm_cap = preflight_history_validated_model_caption(_pf)
            if _pf_vm_cap:
                st.caption(_pf_vm_cap)
            _pf_provider_cap = preflight_history_provider_caption(_pf)
            if _pf_provider_cap:
                st.caption(_pf_provider_cap)
            _pf_sc_cap = preflight_history_sample_count_caption(_pf)
            if _pf_sc_cap:
                st.caption(_pf_sc_cap)
            _pf_ctx_cap = preflight_history_context_tokens_caption(_pf)
            if _pf_ctx_cap:
                st.caption(_pf_ctx_cap)
            _hist = preflight_history_histogram_payload(_pf)
            if _hist and _hist.get("count"):
                _bars = [
                    {
                        "bucket": (
                            f"<={b['le_ms']}ms"
                            if b["le_ms"] is not None
                            else ">10000ms"
                        ),
                        "count": b["count"],
                    }
                    for b in _hist["buckets"]
                ]
                st.bar_chart(
                    _bars,
                    x="bucket",
                    y="count",
                    use_container_width=True,
                )
            _pf_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pf_slug = preflight_history_export_filename_slug(run_id.strip())
            _pf_csv = preflight_history_summary_rows_csv(_pf_rows)
            _pf_json = preflight_history_export_json(_pf)
            _pf_dl_col, _pf_dl_json_col = st.columns(2)
            with _pf_dl_col:
                st.download_button(
                    label="Download preflight timeline CSV",
                    data=_pf_csv.encode("utf-8"),
                    file_name=(
                        "hermes_preflight_timeline_"
                        f"{_pf_slug}_{_pf_ts}.csv"
                    ),
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_preflight_timeline_csv",
                )
            with _pf_dl_json_col:
                st.download_button(
                    label="Download preflight timeline JSON",
                    data=_pf_json.encode("utf-8"),
                    file_name=(
                        "hermes_preflight_timeline_"
                        f"{_pf_slug}_{_pf_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_preflight_timeline_json",
                )
            with st.expander("Raw preflight JSON", expanded=False):
                st.json(_pf)
