from __future__ import annotations

from pathlib import Path

# re-export via bundles/_shared barrel
from nimbusware_console.pages.config_tooling.bundles._shared import *  # noqa: F403


def render_faiss_local_search_panel(*, repo_root: Path) -> None:
    st.text_input(
        "Query (q)",
        placeholder="e.g. auth, rbac, stripe",
        key="hermes_bundle_q",
    )
    st.number_input(
        "Max results (k)",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        key="hermes_bundle_k",
    )
    if st.button("Search catalog", key="hermes_bundle_search_btn"):
        _bq = str(st.session_state.get("hermes_bundle_q", ""))
        _bk = int(st.session_state.get("hermes_bundle_k", 5))
        if not _bq.strip():
            st.warning("Enter a non-empty query.")
        else:
            st.session_state[rl._LAST_BUNDLE_SEARCH_JSON] = run_bundle_catalog_search(
                repo_root,
                _bq,
                k=_bk,
            )
    _bundle_blob = st.session_state.get(rl._LAST_BUNDLE_SEARCH_JSON)
    if isinstance(_bundle_blob, dict) and str(_bundle_blob.get("query", "")).strip():
        _hits_q = str(_bundle_blob.get("query", ""))
        _hits_list = _bundle_blob.get("hits")
        _hits_n = len(_hits_list) if isinstance(_hits_list, list) else None
        _hits_qlen_cap = bundle_search_query_length_caption(
            _hits_q,
            hit_count=_hits_n,
        )
        if _hits_qlen_cap:
            st.caption(_hits_qlen_cap)
        _hits_k_cap = bundle_search_k_caption(_bundle_blob)
        if _hits_k_cap:
            st.caption(_hits_k_cap)
        _hits_sum_cap = bundle_search_hits_summary_caption(_bundle_blob)
        if _hits_sum_cap:
            st.caption(_hits_sum_cap)
        _hits_faiss_cap = bundle_search_faiss_ready_caption(_bundle_blob)
        if _hits_faiss_cap:
            st.caption(_hits_faiss_cap)
        _hits_count_cap = bundle_search_hit_count_caption(_bundle_blob)
        if _hits_count_cap:
            st.caption(_hits_count_cap)
        _hits_top_cap = bundle_search_top_hit_preview_caption(_bundle_blob)
        if _hits_top_cap:
            st.caption(_hits_top_cap)
        st.json(_bundle_blob)
        _empty_hits_cap = bundle_search_empty_hits_readiness_caption(_bundle_blob)
        if _empty_hits_cap:
            st.caption(_empty_hits_cap)
        _hits = bundle_search_hits_from_blob(_bundle_blob)
        if _hits:
            st.caption("Hits (table view)")
            st.dataframe(_hits, use_container_width=True)
            _bs_hits_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _bs_hits_slug = bundle_search_filename_slug(
                str(_bundle_blob.get("query", "")),
            )
            _bs_hits_json = bundle_search_hits_export_json(_hits)
            _bs_hits_csv = bundle_search_hits_table_rows_csv(_hits)
            _bs_hits_dl_json_col, _bs_hits_dl_csv_col = st.columns(2)
            with _bs_hits_dl_json_col:
                st.download_button(
                    label="Download bundle search hits JSON",
                    data=_bs_hits_json.encode("utf-8"),
                    file_name=(f"hermes_bundle_search_hits_{_bs_hits_slug}_{_bs_hits_ts}.json"),
                    mime="application/json",
                    key="hermes_dl_bundle_search_hits_json",
                )
            with _bs_hits_dl_csv_col:
                if _bs_hits_csv:
                    st.download_button(
                        label="Download bundle search hits CSV",
                        data=_bs_hits_csv.encode("utf-8"),
                        file_name=(f"hermes_bundle_search_hits_{_bs_hits_slug}_{_bs_hits_ts}.csv"),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_bundle_search_hits_csv",
                    )
            _stale_cap = bundle_search_after_hits_stale_caption(_bundle_blob)
            if _stale_cap:
                st.caption(_stale_cap)
        _search_metrics = bundle_search_operator_metrics(_bundle_blob)
        _search_metrics_cap = bundle_search_operator_metrics_caption(_search_metrics)
        if _search_metrics_cap:
            st.caption(_search_metrics_cap)
        _search_metric_rows = bundle_search_operator_metrics_table_rows(_search_metrics)
        if _search_metric_rows:
            st.dataframe(_search_metric_rows, use_container_width=True)
        _bs_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _bs_slug = bundle_search_filename_slug(str(_bundle_blob.get("query", "")))
        _search_metrics_slug = bundle_search_operator_metrics_export_filename_slug()
        _search_metrics_json = bundle_search_operator_metrics_export_json(_search_metrics)
        _search_metrics_csv = bundle_search_operator_metrics_table_rows_csv(_search_metric_rows)
        _bs_m_dl1, _bs_m_dl2 = st.columns(2)
        with _bs_m_dl1:
            st.download_button(
                label="Download bundle search operator metrics JSON",
                data=_search_metrics_json.encode("utf-8"),
                file_name=f"hermes_{_search_metrics_slug}_{_bs_slug}_{_bs_ts}.json",
                mime="application/json",
                key="hermes_dl_bundle_search_metrics_json",
            )
        with _bs_m_dl2:
            if _search_metrics_csv:
                st.download_button(
                    label="Download bundle search operator metrics CSV",
                    data=_search_metrics_csv.encode("utf-8"),
                    file_name=f"hermes_{_search_metrics_slug}_{_bs_slug}_{_bs_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_bundle_search_metrics_csv",
                )
        with st.expander("Raw bundle search operator metrics JSON", expanded=False):
            st.json(_search_metrics)
        st.download_button(
            label="Download bundle search JSON",
            data=json.dumps(_bundle_blob, indent=2).encode("utf-8"),
            file_name=f"hermes_bundle_search_{_bs_slug}_{_bs_ts}.json",
            mime="application/json",
            key="hermes_dl_bundle_search_json",
        )
