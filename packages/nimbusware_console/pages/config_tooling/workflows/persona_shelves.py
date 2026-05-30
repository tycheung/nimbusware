from __future__ import annotations

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_workflows_persona_shelves_section() -> None:
    with st.expander("Persona shelves (local repo)", expanded=False):
        st.caption(
            "Read-only: same ``PersonaShelf`` + ``configs/personas/shelves.yaml`` shape as "
            "**GET /v1/personas** (``NIMBUSWARE_REPO_ROOT`` / frozen repo root). No API call.",
        )
        st.caption(persona_catalog_taxonomy_scope_frozen_caption())
        _proot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{_proot}`")
        _cp_sum = critique_pairings_operator_summary(_proot)
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
            if (
                _cp_prod_all_rows
                and type(_cp_prod_key_count) is int
                and _cp_prod_key_count > 12
            ):
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
                        file_name=(
                            f"hermes_{_cp_slug}_critic_counts_full_{_cp_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_critique_pairings_critic_counts_full_json",
                    )
                with _cp_critic_all_dl_csv_col:
                    if _cp_critic_all_csv:
                        st.download_button(
                            label="Download critique pairings critic counts (full) CSV",
                            data=_cp_critic_all_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_cp_slug}_critic_counts_full_{_cp_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_critique_pairings_critic_counts_full_csv",
                        )
            err = _cp_sum.get("load_error")
            if isinstance(err, str) and err.strip():
                st.warning(f"Could not parse critique_pairings.yaml: {err}")
            else:
                with st.expander("critique_pairings.yaml (operator summary)", expanded=False):
                    st.caption(
                        "JSON-safe snapshot of the frozen YAML (§14 #14); not an API payload."
                    )
                    st.json(_cp_sum)
        if st.button("Load persona shelves", key="hermes_persona_load_btn"):
            try:
                st.session_state[rl.rl._LAST_PERSONA_CATALOG_JSON] = load_persona_shelves_catalog(_proot)
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
            with st.expander("Operator summary (fo141)", expanded=False):
                st.caption(
                    "Read-only counts: shelf sizes, total entries, and how many personas "
                    "populate optional fo127 fields."
                )
                _p_op_sum_metrics = persona_catalog_operator_summary_operator_metrics(_psum)
                _p_op_sum_metrics_cap = (
                    persona_catalog_operator_summary_operator_metrics_caption(_p_op_sum_metrics)
                )
                if _p_op_sum_metrics_cap:
                    st.caption(_p_op_sum_metrics_cap)
                _p_op_sum_metric_rows = (
                    persona_catalog_operator_summary_operator_metrics_table_rows(
                        _p_op_sum_metrics,
                    )
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
                _p_op_sum_metrics_json = (
                    persona_catalog_operator_summary_operator_metrics_export_json(
                        _p_op_sum_metrics,
                    )
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
                        file_name=(
                            f"hermes_{_p_op_sum_metrics_slug}_{_p_op_sum_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_persona_operator_summary_metrics_json",
                    )
                with _p_op_sum_m_dl_csv_col:
                    if _p_op_sum_metrics_csv:
                        st.download_button(
                            label="Download operator summary metrics CSV",
                            data=_p_op_sum_metrics_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_p_op_sum_metrics_slug}_{_p_op_sum_ts}.csv"
                            ),
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
                st.caption(
                    "Non-canonical **probation_status** strings by shelf (deduped sample; §14 #14)."
                )
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
