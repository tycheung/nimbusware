from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def _render_persona_catalog_panel(repo_root: Path) -> None:
    if st.button("Load persona shelves", key="hermes_persona_load_btn"):
        try:
            st.session_state[rl.rl._LAST_PERSONA_CATALOG_JSON] = load_persona_shelves_catalog(
                _proot
            )
        except FileNotFoundError as exc:
            st.error(str(exc))
        except ValueError as exc:
            st.error(f"Invalid persona shelves YAML: {exc}")
    _persona_blob = st.session_state.get(rl._LAST_PERSONA_CATALOG_JSON)
    if isinstance(_persona_blob, dict) and _persona_blob:
        st.json(_persona_blob)
        _p_dn_cap = persona_catalog_display_name_length_caption(_persona_blob)
        if _p_dn_cap:
            st.caption(_p_dn_cap)
        _p_id_cap = persona_catalog_persona_id_length_caption(_persona_blob)
        if _p_id_cap:
            st.caption(_p_id_cap)
        _psum = persona_catalog_operator_summary(_persona_blob)
        _p_empty_id_cap = persona_catalog_empty_id_operator_caption(_psum)
        if _p_empty_id_cap:
            st.caption(_p_empty_id_cap)
        _p_dup_dn_cap = persona_catalog_display_name_duplicates_operator_caption(_psum)
        if _p_dup_dn_cap:
            st.caption(_p_dup_dn_cap)
        _p_dup_id_cap = persona_catalog_persona_id_duplicates_operator_caption(_psum)
        if _p_dup_id_cap:
            st.caption(_p_dup_id_cap)
        _p_prob_cap = persona_catalog_probation_breakdown_caption(_psum)
        if _p_prob_cap:
            st.caption(_p_prob_cap)
        _p_woi_cap = persona_catalog_without_instructions_caption(_psum)
        if _p_woi_cap:
            st.caption(_p_woi_cap)
        _p_wocp_cap = persona_catalog_without_capability_profile_caption(_psum)
        if _p_wocp_cap:
            st.caption(_p_wocp_cap)
        with st.expander("Operator summary", expanded=False):
            st.caption(
                "Read-only counts: shelf sizes, total entries, and how many personas "
                "populate optional catalog fields."
            )
            _p_op_sum_metrics = persona_catalog_operator_summary_operator_metrics(_psum)
            _p_op_sum_metrics_cap = persona_catalog_operator_summary_operator_metrics_caption(
                _p_op_sum_metrics
            )
            if _p_op_sum_metrics_cap:
                st.caption(_p_op_sum_metrics_cap)
            _p_op_sum_metric_rows = persona_catalog_operator_summary_operator_metrics_table_rows(
                _p_op_sum_metrics,
            )
            if _p_op_sum_metric_rows:
                st.dataframe(
                    _p_op_sum_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
            _p_op_sum_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _p_op_sum_metrics_slug = (
                persona_catalog_operator_summary_operator_metrics_export_filename_slug()
            )
            _p_op_sum_metrics_json = persona_catalog_operator_summary_operator_metrics_export_json(
                _p_op_sum_metrics,
            )
            _p_op_sum_metrics_csv = (
                persona_catalog_operator_summary_operator_metrics_table_rows_csv(
                    _p_op_sum_metric_rows,
                )
            )
            _p_op_sum_m_dl_json_col, _p_op_sum_m_dl_csv_col = st.columns(2)
            with _p_op_sum_m_dl_json_col:
                st.download_button(
                    label="Download operator summary metrics JSON",
                    data=_p_op_sum_metrics_json.encode("utf-8"),
                    file_name=(f"hermes_{_p_op_sum_metrics_slug}_{_p_op_sum_ts}.json"),
                    mime="application/json",
                    key="hermes_dl_persona_operator_summary_metrics_json",
                )
            with _p_op_sum_m_dl_csv_col:
                if _p_op_sum_metrics_csv:
                    st.download_button(
                        label="Download operator summary metrics CSV",
                        data=_p_op_sum_metrics_csv.encode("utf-8"),
                        file_name=(f"hermes_{_p_op_sum_metrics_slug}_{_p_op_sum_ts}.csv"),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_operator_summary_metrics_csv",
                    )
            _p_op_sum_json = persona_catalog_operator_summary_export_json(_psum)
            _p_op_sum_csv = persona_catalog_operator_summary_table_rows_csv(_psum)
            _p_op_sum_dl_json_col, _p_op_sum_dl_csv_col = st.columns(2)
            with _p_op_sum_dl_json_col:
                st.download_button(
                    label="Download operator summary JSON",
                    data=_p_op_sum_json.encode("utf-8"),
                    file_name=f"hermes_persona_operator_summary_{_p_op_sum_ts}.json",
                    mime="application/json",
                    key="hermes_dl_persona_operator_summary_json",
                )
            with _p_op_sum_dl_csv_col:
                if _p_op_sum_csv:
                    st.download_button(
                        label="Download operator summary CSV",
                        data=_p_op_sum_csv.encode("utf-8"),
                        file_name=f"hermes_persona_operator_summary_{_p_op_sum_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_operator_summary_csv",
                    )
            st.json(_psum)
        _p_other_rows = persona_probation_other_examples_by_shelf_table_rows(_psum)
        if _p_other_rows:
            st.caption("Non-canonical **probation_status** strings by shelf (deduped sample).")
            st.dataframe(_p_other_rows, use_container_width=True, hide_index=True)
            _p_other_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _p_other_slug = persona_probation_other_export_filename_slug()
            _p_other_json = persona_probation_other_by_shelf_export_json(_p_other_rows)
            _p_other_csv = persona_probation_other_by_shelf_table_rows_csv(_p_other_rows)
            _p_other_dl_csv_col, _p_other_dl_json_col = st.columns(2)
            with _p_other_dl_csv_col:
                if _p_other_csv:
                    st.download_button(
                        label="Download probation other examples CSV",
                        data=_p_other_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_persona_probation_other_{_p_other_slug}_{_p_other_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_probation_other_csv",
                    )
            with _p_other_dl_json_col:
                st.download_button(
                    label="Download probation other examples JSON",
                    data=_p_other_json.encode("utf-8"),
                    file_name=(
                        f"hermes_persona_probation_other_{_p_other_slug}_{_p_other_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_persona_probation_other_json",
                )
        _prows = persona_catalog_flat_rows(_persona_blob)
        if _prows:
            st.text_input(
                "Filter table: id / display_name substring (case-insensitive)",
                key="hermes_persona_catalog_filter_q",
            )
            st.selectbox(
                "Shelf filter",
                options=("all", "business_area", "development_role"),
                key="hermes_persona_catalog_filter_shelf",
            )
            st.selectbox(
                "Probation status filter",
                options=("all", "probation", "promoted", "shelved", "(unset)"),
                key="hermes_persona_catalog_filter_probation",
            )
            _p_tool_opts = ("all", *persona_catalog_distinct_allowed_tools(_persona_blob))
            st.selectbox(
                "Allowed tool filter (interim tags UX)",
                options=_p_tool_opts,
                key="hermes_persona_catalog_filter_allowed_tool",
            )
            _pq = str(st.session_state.get("hermes_persona_catalog_filter_q", "")).strip()
            _psel = str(st.session_state.get("hermes_persona_catalog_filter_shelf", "all"))
            _shelf_arg = None if _psel == "all" else _psel
            _pprob = str(
                st.session_state.get("hermes_persona_catalog_filter_probation", "all"),
            ).strip()
            _ptool = str(
                st.session_state.get("hermes_persona_catalog_filter_allowed_tool", "all"),
            ).strip()
            _pview = filter_persona_catalog_flat_rows(
                _prows,
                query=_pq,
                shelf=_shelf_arg,
                probation_status=_pprob,
                allowed_tool=_ptool,
            )
            _p_tool_cap = persona_catalog_allowed_tool_filter_caption(
                _ptool,
                match_count=len(_pview),
                total_count=len(_prows),
            )
            if _p_tool_cap:
                st.caption(_p_tool_cap)
            st.caption("Entries (table view — filtered)")
            st.dataframe(_pview, use_container_width=True)
            _pts_flat = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _pflat_slug = persona_catalog_flat_export_filename_slug()
            _csv_body = persona_catalog_flat_rows_csv(_pview)
            _json_body = persona_catalog_flat_rows_export_json(_pview)
            _pflat_dl_csv_col, _pflat_dl_json_col = st.columns(2)
            with _pflat_dl_csv_col:
                if _csv_body:
                    st.download_button(
                        label="Download filtered table as CSV",
                        data=_csv_body.encode("utf-8"),
                        file_name=f"hermes_persona_shelves_flat_{_pflat_slug}_{_pts_flat}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_persona_catalog_csv",
                    )
            with _pflat_dl_json_col:
                if _pview:
                    st.download_button(
                        label="Download filtered table as JSON",
                        data=_json_body.encode("utf-8"),
                        file_name=f"hermes_persona_shelves_flat_{_pflat_slug}_{_pts_flat}.json",
                        mime="application/json",
                        key="hermes_dl_persona_catalog_flat_json",
                    )
        _pts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        st.download_button(
            label="Download persona shelves JSON",
            data=json.dumps(_persona_blob, indent=2).encode("utf-8"),
            file_name=f"hermes_persona_shelves_{_pts}.json",
            mime="application/json",
            key="hermes_dl_persona_catalog_json",
        )
