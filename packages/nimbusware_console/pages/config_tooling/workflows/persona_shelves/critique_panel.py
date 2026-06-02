from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def _render_critique_pairings_panel(repo_root: Path) -> None:
    _cp_sum = critique_pairings_operator_summary(repo_root)
    _cp_metrics = critique_pairings_operator_summary_operator_metrics(_cp_sum)
    _cp_metrics_cap = critique_pairings_operator_summary_operator_metrics_caption(_cp_metrics)
    if _cp_metrics_cap:
        st.caption(_cp_metrics_cap)
    _cp_metric_rows = critique_pairings_operator_summary_operator_metrics_table_rows(
        _cp_metrics,
    )
    if _cp_metric_rows:
        st.dataframe(_cp_metric_rows, use_container_width=True, hide_index=True)
    _cp_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _cp_metrics_slug = critique_pairings_operator_summary_operator_metrics_export_filename_slug()
    _cp_metrics_json = critique_pairings_operator_summary_operator_metrics_export_json(
        _cp_metrics,
    )
    _cp_metrics_csv = critique_pairings_operator_summary_operator_metrics_table_rows_csv(
        _cp_metric_rows,
    )
    _cp_m_dl_json_col, _cp_m_dl_csv_col = st.columns(2)
    with _cp_m_dl_json_col:
        st.download_button(
            label="Download critique pairings operator metrics JSON",
            data=_cp_metrics_json.encode("utf-8"),
            file_name=f"hermes_{_cp_metrics_slug}_{_cp_metrics_ts}.json",
            mime="application/json",
            key="hermes_dl_critique_pairings_operator_metrics_json",
        )
    with _cp_m_dl_csv_col:
        if _cp_metrics_csv:
            st.download_button(
                label="Download critique pairings operator metrics CSV",
                data=_cp_metrics_csv.encode("utf-8"),
                file_name=f"hermes_{_cp_metrics_slug}_{_cp_metrics_ts}.csv",
                mime="text/csv; charset=utf-8",
                key="hermes_dl_critique_pairings_operator_metrics_csv",
            )
    if _cp_sum.get("has_critique_pairings_yaml"):
        st.caption(
            "Read-only **critique_pairings.yaml**: "
            f"version `{_cp_sum.get('version')!r}`, "
            f"{_cp_sum.get('producer_taxonomy_key_count')} producer taxonomy key(s)."
        )
        _cp_total_cap = persona_catalog_critique_pairings_total_caption(_cp_sum)
        if _cp_total_cap:
            st.caption(_cp_total_cap)
        sample = _cp_sum.get("producer_taxonomy_keys_sample") or []
        if isinstance(sample, list) and sample:
            vis = ", ".join(f"``{x}``" for x in sample if isinstance(x, str) and x.strip())
            if vis:
                st.caption("Sample producer keys: " + vis + ".")
        _cp_prod_rows = critique_pairings_producer_keys_table_rows(_cp_sum)
        if _cp_prod_rows:
            _cp_prod_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _cp_prod_slug = critique_pairings_export_filename_slug()
            _cp_prod_json = critique_pairings_producer_keys_export_json(_cp_prod_rows)
            _cp_prod_csv = critique_pairings_producer_keys_table_rows_csv(_cp_prod_rows)
            _cp_prod_dl_json_col, _cp_prod_dl_csv_col = st.columns(2)
            with _cp_prod_dl_json_col:
                st.download_button(
                    label="Download critique pairings producer keys JSON",
                    data=_cp_prod_json.encode("utf-8"),
                    file_name=f"hermes_{_cp_prod_slug}_producer_keys_{_cp_prod_ts}.json",
                    mime="application/json",
                    key="hermes_dl_critique_pairings_producer_keys_json",
                )
            with _cp_prod_dl_csv_col:
                if _cp_prod_csv:
                    st.download_button(
                        label="Download critique pairings producer keys CSV",
                        data=_cp_prod_csv.encode("utf-8"),
                        file_name=f"hermes_{_cp_prod_slug}_producer_keys_{_cp_prod_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_producer_keys_csv",
                    )
        _cp_prod_key_count = _cp_sum.get("producer_taxonomy_key_count")
        _cp_prod_all_rows = critique_pairings_producer_keys_all_table_rows(_cp_sum)
        if _cp_prod_all_rows and type(_cp_prod_key_count) is int and _cp_prod_key_count > 12:
            _cp_prod_all_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _cp_prod_all_slug = critique_pairings_export_filename_slug()
            _cp_prod_all_json = critique_pairings_producer_keys_all_export_json(
                _cp_prod_all_rows,
            )
            _cp_prod_all_csv = critique_pairings_producer_keys_all_table_rows_csv(
                _cp_prod_all_rows,
            )
            _cp_prod_all_dl_json_col, _cp_prod_all_dl_csv_col = st.columns(2)
            with _cp_prod_all_dl_json_col:
                st.download_button(
                    label="Download critique pairings producer keys (full) JSON",
                    data=_cp_prod_all_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_cp_prod_all_slug}_producer_keys_full_{_cp_prod_all_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_critique_pairings_producer_keys_full_json",
                )
            with _cp_prod_all_dl_csv_col:
                if _cp_prod_all_csv:
                    st.download_button(
                        label="Download critique pairings producer keys (full) CSV",
                        data=_cp_prod_all_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_cp_prod_all_slug}_producer_keys_full_{_cp_prod_all_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_producer_keys_full_csv",
                    )
        _cp_total = _cp_sum.get("critique_pairing_critic_role_entries_total")
        if type(_cp_total) is int and _cp_total > 0:
            st.caption(
                "Critique pairings: **"
                + str(_cp_total)
                + "** critic role list entr(y/ies) across producers (non-empty strings)."
            )
        _cp_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        _cp_slug = critique_pairings_export_filename_slug()
        _cp_json = critique_pairings_operator_summary_export_json(_cp_sum)
        st.download_button(
            label="Download critique pairings summary JSON",
            data=_cp_json.encode("utf-8"),
            file_name=f"hermes_{_cp_slug}_{_cp_ts}.json",
            mime="application/json",
            key="hermes_dl_critique_pairings_summary_json",
        )
        _cp_critic_rows = critique_pairings_critic_counts_table_rows(_cp_sum)
        if _cp_critic_rows:
            _cp_critic_json = critique_pairings_critic_counts_export_json(_cp_critic_rows)
            _cp_critic_csv = critique_pairings_critic_counts_table_rows_csv(_cp_critic_rows)
            _cp_critic_dl_json_col, _cp_critic_dl_csv_col = st.columns(2)
            with _cp_critic_dl_json_col:
                st.download_button(
                    label="Download critique pairings critic counts JSON",
                    data=_cp_critic_json.encode("utf-8"),
                    file_name=f"hermes_{_cp_slug}_critic_counts_{_cp_ts}.json",
                    mime="application/json",
                    key="hermes_dl_critique_pairings_critic_counts_json",
                )
            with _cp_critic_dl_csv_col:
                if _cp_critic_csv:
                    st.download_button(
                        label="Download critique pairings critic counts CSV",
                        data=_cp_critic_csv.encode("utf-8"),
                        file_name=f"hermes_{_cp_slug}_critic_counts_{_cp_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_critic_counts_csv",
                    )
        _cp_critic_all_rows = critique_pairings_critic_counts_all_table_rows(_cp_sum)
        _cp_critic_sample_rows = critique_pairings_critic_counts_table_rows(_cp_sum)
        if _cp_critic_all_rows and len(_cp_critic_all_rows) > len(_cp_critic_sample_rows):
            _cp_critic_all_json = critique_pairings_critic_counts_all_export_json(
                _cp_critic_all_rows,
            )
            _cp_critic_all_csv = critique_pairings_critic_counts_all_table_rows_csv(
                _cp_critic_all_rows,
            )
            _cp_critic_all_dl_json_col, _cp_critic_all_dl_csv_col = st.columns(2)
            with _cp_critic_all_dl_json_col:
                st.download_button(
                    label="Download critique pairings critic counts (full) JSON",
                    data=_cp_critic_all_json.encode("utf-8"),
                    file_name=(f"hermes_{_cp_slug}_critic_counts_full_{_cp_ts}.json"),
                    mime="application/json",
                    key="hermes_dl_critique_pairings_critic_counts_full_json",
                )
            with _cp_critic_all_dl_csv_col:
                if _cp_critic_all_csv:
                    st.download_button(
                        label="Download critique pairings critic counts (full) CSV",
                        data=_cp_critic_all_csv.encode("utf-8"),
                        file_name=(f"hermes_{_cp_slug}_critic_counts_full_{_cp_ts}.csv"),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_critique_pairings_critic_counts_full_csv",
                    )
        err = _cp_sum.get("load_error")
        if isinstance(err, str) and err.strip():
            st.warning(f"Could not parse critique_pairings.yaml: {err}")
        else:
            with st.expander("critique_pairings.yaml (operator summary)", expanded=False):
                st.caption("JSON-safe snapshot of the frozen YAML; not an API payload.")
                st.json(_cp_sum)
