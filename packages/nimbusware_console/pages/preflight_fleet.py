from __future__ import annotations

from datetime import datetime, timezone

from nimbusware_client.http import HTTPError
import streamlit as st

from nimbusware_console.pages import _state as rl
from nimbusware_console.preflight_cross_run_display import (
    fetch_preflight_history,
    preflight_cross_run_trend_rows,
    preflight_history_metrics_export_download_filename_slug,
    preflight_history_metrics_export_download_json,
    preflight_history_response_limit,
    preflight_history_response_metrics_export_caption,
    preflight_history_response_sli_caption,
    preflight_pairs_from_history_response,
)


def render_preflight_fleet_section() -> None:
        with st.expander("Cross-run preflight trends (from last list)", expanded=False):
            st.caption(
                "Calls **GET /v1/preflight-history** (bounded fleet aggregation; same top-level "
                "``preflight`` projection as **Preflight history (from timeline)**). Requests "
                "``include_metrics_export=1`` for fleet SLI captions and a metrics-export JSON "
                "download when present. **run_index** follows API order (``1`` = first entry, "
                "usually newest when ``order=newest_first``). When the last run list had more "
                "ids than the cap, history may return fewer rows than the list page."
            )
            st.number_input(
                "Max runs to scan (cap)",
                min_value=1,
                max_value=15,
                value=10,
                step=1,
                key="hermes_preflight_trend_cap",
            )
            _list_for_trend = st.session_state.get(rl._LAST_LIST_JSON)
            _ids_trend: list[str] = []
            if isinstance(_list_for_trend, dict):
                _raw_ids = _list_for_trend.get("run_ids") or []
                if isinstance(_raw_ids, list):
                    _ids_trend = [str(x).strip() for x in _raw_ids if str(x).strip()]
            if not _ids_trend:
                st.info("Refresh the run list above first so run_ids are available.")
            elif st.button("Load preflight trend", key="hermes_preflight_trend_btn"):
                _cap = int(st.session_state.get("hermes_preflight_trend_cap", 10))
                _cap = max(1, min(15, _cap))
                _slice = _ids_trend[:_cap]
                _trend_fetch_errs: list[str] = []
                try:
                    from nimbusware_console.enterprise_console_ui import (
                        enterprise_preflight_headers_for_cross_run,
                    )

                    _hist_body = fetch_preflight_history(
                        limit=_cap,
                        include_metrics_export=True,
                        headers=enterprise_preflight_headers_for_cross_run(),
                    )
                    _pairs = preflight_pairs_from_history_response(_hist_body)
                    st.session_state[rl._PREFLIGHT_TREND_HISTORY_BODY] = _hist_body
                    st.session_state.pop(rl._PREFLIGHT_TREND_ERR, None)
                except HTTPError as _exc:
                    _pairs = []
                    _trend_fetch_errs.append(str(_exc))
                    st.session_state.pop(rl._PREFLIGHT_TREND_HISTORY_BODY, None)
                _rows_t = preflight_cross_run_trend_rows(_pairs)
                st.session_state[rl._PREFLIGHT_TREND_ROWS] = _rows_t
                if _trend_fetch_errs:
                    st.session_state[rl._PREFLIGHT_TREND_ERR] = _trend_fetch_errs
                else:
                    st.session_state.pop(rl._PREFLIGHT_TREND_ERR, None)

            _trend_rows = st.session_state.get(rl._PREFLIGHT_TREND_ROWS)
            _trend_errs = st.session_state.get(rl._PREFLIGHT_TREND_ERR)
            if isinstance(_trend_errs, list) and _trend_errs:
                for _ln in _trend_errs[:8]:
                    st.warning(str(_ln))
                if len(_trend_errs) > 8:
                    st.caption(f"(+{len(_trend_errs) - 8} more preflight-history errors)")
            _hist_saved = st.session_state.get(rl._PREFLIGHT_TREND_HISTORY_BODY)
            if isinstance(_hist_saved, dict) and _ids_trend:
                _cap_saved = int(st.session_state.get("hermes_preflight_trend_cap", 10))
                _cap_saved = max(1, min(15, _cap_saved))
                _list_slice_len = min(len(_ids_trend), _cap_saved)
                _returned = len(_hist_saved.get("entries") or [])
                _api_lim = preflight_history_response_limit(_hist_saved)
                _pf_export_cap = preflight_history_response_metrics_export_caption(_hist_saved)
                if _pf_export_cap:
                    st.caption(_pf_export_cap)
                _pf_sli_cap = preflight_history_response_sli_caption(_hist_saved)
                if _pf_sli_cap:
                    st.caption(_pf_sli_cap)
                _pf_hist_export_json = preflight_history_metrics_export_download_json(
                    _hist_saved,
                )
                if _pf_hist_export_json != "{}":
                    _pf_hist_export_slug = (
                        preflight_history_metrics_export_download_filename_slug()
                    )
                    _pf_hist_export_ts = datetime.now(timezone.utc).strftime(
                        "%Y%m%dT%H%M%SZ",
                    )
                    st.download_button(
                        label="Download fleet preflight metrics export JSON",
                        data=_pf_hist_export_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_pf_hist_export_slug}_{_pf_hist_export_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_preflight_history_metrics_export_json",
                    )
                if _returned < _list_slice_len:
                    _lim_note = f" (API limit {_api_lim})" if _api_lim is not None else ""
                    st.caption(
                        f"Preflight history returned **{_returned}** run(s) for a list slice of "
                        f"**{_list_slice_len}**{_lim_note}; fleet order may differ from the run list."
                    )
            if isinstance(_trend_rows, list) and _trend_rows:
                _sum = preflight_cross_run_trend_summary(_trend_rows)
                st.caption(
                    f"Scanned {_sum['runs']} runs — {_sum['with_preflight_projection']} with "
                    f"preflight projection, {_sum['with_p95_latency']} with usable p95."
                )
                _sample_cov_cap = preflight_cross_run_latency_sample_count_coverage_caption(
                    _trend_rows,
                )
                if _sample_cov_cap:
                    st.caption(_sample_cov_cap)
                _checks_cov_cap = preflight_cross_run_checks_passed_coverage_caption(_trend_rows)
                if _checks_cov_cap:
                    st.caption(_checks_cov_cap)
                _p95_spread_cap = preflight_cross_run_p95_spread_caption(_trend_rows)
                if _p95_spread_cap:
                    st.caption(_p95_spread_cap)
                _multi_cap = preflight_cross_run_multisample_caption(_trend_rows)
                if _multi_cap:
                    st.caption(_multi_cap)
                _vm_cov_cap = preflight_cross_run_validated_model_id_coverage_caption(_trend_rows)
                if _vm_cov_cap:
                    st.caption(_vm_cov_cap)
                _depth_cap = preflight_cross_run_operator_depth_caption(_trend_rows)
                if _depth_cap:
                    st.caption(_depth_cap)
                _pref_trend_metrics = preflight_cross_run_operator_metrics(_sum)
                _pref_trend_metrics_cap = preflight_cross_run_operator_metrics_caption(
                    _pref_trend_metrics,
                )
                if _pref_trend_metrics_cap:
                    st.caption(_pref_trend_metrics_cap)
                _pref_trend_metric_rows = preflight_cross_run_operator_metrics_table_rows(
                    _pref_trend_metrics,
                )
                _pref_trend_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _pref_trend_slug = preflight_cross_run_trend_export_filename_slug()
                _pref_trend_metrics_slug = (
                    preflight_cross_run_operator_metrics_export_filename_slug()
                )
                if _pref_trend_metric_rows:
                    st.dataframe(
                        _pref_trend_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _pref_trend_metrics_json = (
                        preflight_cross_run_operator_metrics_export_json(
                            _pref_trend_metrics,
                        )
                    )
                    _pref_trend_metrics_csv = (
                        preflight_cross_run_operator_metrics_table_rows_csv(
                            _pref_trend_metric_rows,
                        )
                    )
                    (
                        _pref_trend_metrics_dl_json_col,
                        _pref_trend_metrics_dl_csv_col,
                    ) = st.columns(2)
                    with _pref_trend_metrics_dl_json_col:
                        st.download_button(
                            label=(
                                "Download preflight cross-run operator "
                                "metrics JSON"
                            ),
                            data=_pref_trend_metrics_json.encode("utf-8"),
                            file_name=(
                                "hermes_preflight_cross_run_operator_metrics_"
                                f"{_pref_trend_metrics_slug}_{_pref_trend_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_preflight_cross_run_operator_metrics_json",
                        )
                    with _pref_trend_metrics_dl_csv_col:
                        if _pref_trend_metrics_csv:
                            st.download_button(
                                label=(
                                    "Download preflight cross-run operator "
                                    "metrics CSV"
                                ),
                                data=_pref_trend_metrics_csv.encode("utf-8"),
                                file_name=(
                                    "hermes_preflight_cross_run_operator_metrics_"
                                    f"{_pref_trend_metrics_slug}_{_pref_trend_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_preflight_cross_run_operator_metrics_csv",
                            )
                st.dataframe(_trend_rows, use_container_width=True, hide_index=True)
                _pref_trend_csv = preflight_cross_run_trend_rows_csv(_trend_rows)
                _pref_trend_json = preflight_cross_run_trend_export_json(_trend_rows)
                _pref_trend_dl_col, _pref_trend_dl_json_col = st.columns(2)
                with _pref_trend_dl_col:
                    st.download_button(
                        label="Download preflight cross-run trend CSV",
                        data=_pref_trend_csv.encode("utf-8"),
                        file_name=f"hermes_preflight_cross_run_{_pref_trend_slug}_{_pref_trend_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_preflight_cross_run_csv",
                    )
                with _pref_trend_dl_json_col:
                    st.download_button(
                        label="Download preflight cross-run trend JSON",
                        data=_pref_trend_json.encode("utf-8"),
                        file_name=f"hermes_preflight_cross_run_{_pref_trend_slug}_{_pref_trend_ts}.json",
                        mime="application/json",
                        key="hermes_dl_preflight_cross_run_json",
                    )
                _xs = [int(r["run_index"]) for r in _trend_rows if isinstance(r, dict)]
                _y_p95 = [
                    float(r["p95_latency_ms"])
                    if isinstance(r, dict) and isinstance(r.get("p95_latency_ms"), int)
                    else math.nan
                    for r in _trend_rows
                ]
                _y_sc = [
                    float(r["sample_count"])
                    if isinstance(r, dict) and isinstance(r.get("sample_count"), int)
                    else math.nan
                    for r in _trend_rows
                ]
                st.caption("p95 latency (ms) vs run_index (missing points are gaps in the line).")
                st.line_chart(
                    {"run_index": _xs, "p95_latency_ms": _y_p95},
                    x="run_index",
                    y="p95_latency_ms",
                )
                st.caption("Preflight sample count vs run_index (when reported).")
                st.line_chart(
                    {"run_index": _xs, "sample_count": _y_sc},
                    x="run_index",
                    y="sample_count",
                )
                with st.expander("Raw preflight trend rows JSON", expanded=False):
                    st.json(_trend_rows)

