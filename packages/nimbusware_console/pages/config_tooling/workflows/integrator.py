"""Config tooling — integrator section."""

from __future__ import annotations

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_workflows_integrator_section() -> None:
    with st.expander("Module Integrator gate (workflow preview)", expanded=False):
        st.caption(
            "**fo131** read-only preview + **fo132** / **fo140** optional subtree disk apply + "
            "**§14 #13** optional **full-profile** shallow merge + **fo133** "
            "threshold source "
            "breakdown + **fo134** universal critique + **fo135** self-refinement + **fo136** "
            "security-scan-metadata + **fo137** escalation-suppress + **fo139** "
            "agent-evaluator workflow explainer "
            "(nested expanders): preview "
            "``ModuleIntegrator.score_fit`` against ``configs/bundles/catalog.yaml`` using the same "
            "``integrator_gate`` knobs as the orchestrator (workflow YAML + "
            "``configs/integrator/thresholds.yaml``; "
            "``HERMES_INTEGRATOR_MIN_SCORE_TO_PASS`` still wins "
            "when set). Paste an ``integrator_gate:`` fragment to override **min_score** / "
            "**enabled** / "
            "**project_tags** for preview; **Apply** (fo132 / fo140) merges only that subtree when "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}`` is enabled and you confirm the profile stem.",
        )
        _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
        st.caption(f"Effective repo root: `{_iroot}`")
        _wf_keys = list_workflow_profile_keys(_iroot)
        if not _wf_keys:
            st.warning("No workflow profiles found under ``configs/workflows/``.")
            _wf_pick: str | None = None
        else:
            _wf_pick = st.selectbox(
                "Workflow profile (YAML stem)",
                options=_wf_keys,
                index=_wf_keys.index("default") if "default" in _wf_keys else 0,
                key="hermes_integrator_wf_profile",
            )
        with st.expander("Universal critique (workflow YAML, fo134)", expanded=False):
            st.caption(
                "Read-only: ``universal_critique`` from the **same** workflow profile as integrator "
                "preview — **yaml_only** is frozen file content; **effective_with_env** applies "
                "non-empty ``HERMES_*`` critique env overrides (same rules as the orchestrator). "
                "PLAN_GAP §14 #16."
            )
            _uc_expl = universal_critique_workflow_explainer_payload(
                _iroot,
                workflow_profile=_wf_pick,
            )
            _uc_expl_metrics = universal_critique_workflow_explainer_operator_metrics(_uc_expl)
            _uc_expl_metrics_cap = universal_critique_workflow_explainer_operator_metrics_caption(
                _uc_expl_metrics,
            )
            if _uc_expl_metrics_cap:
                st.caption(_uc_expl_metrics_cap)
            _uc_expl_metric_rows = universal_critique_workflow_explainer_operator_metrics_table_rows(
                _uc_expl_metrics,
            )
            if _uc_expl_metric_rows:
                st.dataframe(_uc_expl_metric_rows, use_container_width=True, hide_index=True)
            _uc_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _uc_expl_metrics_slug = (
                universal_critique_workflow_explainer_operator_metrics_export_filename_slug()
            )
            _uc_expl_metrics_json = universal_critique_workflow_explainer_operator_metrics_export_json(
                _uc_expl_metrics,
            )
            _uc_expl_metrics_csv = (
                universal_critique_workflow_explainer_operator_metrics_table_rows_csv(
                    _uc_expl_metric_rows,
                )
            )
            _uc_expl_m_dl_json_col, _uc_expl_m_dl_csv_col = st.columns(2)
            with _uc_expl_m_dl_json_col:
                st.download_button(
                    label="Download universal critique operator metrics JSON",
                    data=_uc_expl_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_uc_expl_metrics_slug}_{_uc_expl_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_universal_critique_explainer_metrics_json",
                )
            with _uc_expl_m_dl_csv_col:
                if _uc_expl_metrics_csv:
                    st.download_button(
                        label="Download universal critique operator metrics CSV",
                        data=_uc_expl_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_uc_expl_metrics_slug}_{_uc_expl_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_universal_critique_explainer_metrics_csv",
                    )
            _uc_enabled_cap = universal_critique_enabled_stages_caption(_uc_expl)
            if _uc_enabled_cap:
                st.caption(_uc_enabled_cap)
            _uc_default_cap = universal_critique_default_enabled_caption(_uc_expl)
            if _uc_default_cap:
                st.caption(_uc_default_cap)
            _uc_present_cap = universal_critique_yaml_present_caption(_uc_expl)
            if _uc_present_cap:
                st.caption(_uc_present_cap)
            _uc_relpath_cap = universal_critique_workflow_yaml_relpath_caption(_uc_expl)
            if _uc_relpath_cap:
                st.caption(_uc_relpath_cap)
            _uc_bytes_cap = universal_critique_workflow_yaml_bytes_caption(_uc_expl)
            if _uc_bytes_cap:
                st.caption(_uc_bytes_cap)
            _uc_nonempty_cap = universal_critique_yaml_top_level_nonempty_count_caption(
                _uc_expl,
            )
            if _uc_nonempty_cap:
                st.caption(_uc_nonempty_cap)
            _uc_enabled_true_cap = universal_critique_yaml_top_level_enabled_true_count_caption(
                _uc_expl,
            )
            if _uc_enabled_true_cap:
                st.caption(_uc_enabled_true_cap)
            _uc_enabled_false_cap = universal_critique_yaml_top_level_enabled_false_count_caption(
                _uc_expl,
            )
            if _uc_enabled_false_cap:
                st.caption(_uc_enabled_false_cap)
            _uc_mapping_child_cap = universal_critique_yaml_top_level_mapping_child_count_caption(
                _uc_expl,
            )
            if _uc_mapping_child_cap:
                st.caption(_uc_mapping_child_cap)
            _uc_list_child_cap = universal_critique_yaml_top_level_list_child_count_caption(
                _uc_expl,
            )
            if _uc_list_child_cap:
                st.caption(_uc_list_child_cap)
            _uc_bucket_cap = universal_critique_yaml_enabled_bucket_caption(_uc_expl)
            if _uc_bucket_cap:
                st.caption(_uc_bucket_cap)
            _uc_stage_keys_cap = universal_critique_yaml_stage_keys_caption(_uc_expl)
            if _uc_stage_keys_cap:
                st.caption(_uc_stage_keys_cap)
            _uc_rows = [
                {
                    "field": "universal_critique block in YAML",
                    "value": str(_uc_expl.get("universal_critique_yaml_present")),
                },
                {
                    "field": "universal_critique YAML top-level keys",
                    "value": ", ".join(_uc_expl.get("universal_critique_yaml_top_level_keys") or [])
                    or "—",
                },
                {
                    "field": "universal_critique YAML top-level nonempty value count",
                    "value": str(_uc_expl.get("universal_critique_yaml_top_level_nonempty_count")),
                },
                {
                    "field": "universal_critique YAML top-level enabled: true subtree count",
                    "value": str(
                        _uc_expl.get("universal_critique_yaml_top_level_enabled_true_count"),
                    ),
                },
                {
                    "field": "universal_critique YAML top-level enabled: false subtree count",
                    "value": str(
                        _uc_expl.get("universal_critique_yaml_top_level_enabled_false_count"),
                    ),
                },
                {
                    "field": "universal_critique YAML top-level mapping child count",
                    "value": str(
                        _uc_expl.get("universal_critique_yaml_top_level_mapping_child_count"),
                    ),
                },
                {
                    "field": "universal_critique YAML top-level scalar/null leaf count",
                    "value": str(
                        _uc_expl.get("universal_critique_yaml_top_level_scalar_leaf_count"),
                    ),
                },
                {
                    "field": "universal_critique YAML top-level list child count",
                    "value": str(
                        _uc_expl.get("universal_critique_yaml_top_level_list_child_count"),
                    ),
                },
                {
                    "field": "universal_critique YAML mapping children without enabled key",
                    "value": str(
                        _uc_expl.get(
                            "universal_critique_yaml_top_level_enabled_unset_mapping_count",
                        ),
                    ),
                },
                {
                    "field": "workflow YAML file size (bytes, on disk)",
                    "value": "—"
                    if _uc_expl.get("universal_critique_workflow_yaml_bytes") is None
                    else str(_uc_expl.get("universal_critique_workflow_yaml_bytes")),
                },
                {
                    "field": "implementation LLM (effective)",
                    "value": str(_uc_expl.get("effective_with_env", {}).get("impl_llm")),
                },
                {
                    "field": "implementation stub (effective)",
                    "value": str(_uc_expl.get("effective_with_env", {}).get("impl_stub")),
                },
                {
                    "field": "test_writer enabled (effective)",
                    "value": str(_uc_expl.get("effective_with_env", {}).get("tw_enabled")),
                },
                {
                    "field": "planner enabled (effective)",
                    "value": str(_uc_expl.get("effective_with_env", {}).get("pll_enabled")),
                },
            ]
            st.dataframe(_uc_rows, use_container_width=True, hide_index=True)
            _uc_delta = universal_critique_env_override_deltas(_uc_expl)
            if _uc_delta:
                st.caption("Env overrides vs frozen YAML (non-matching knobs only; §14 #16).")
                st.dataframe(_uc_delta, use_container_width=True, hide_index=True)
            _uc_delta_cap = universal_critique_env_override_summary_caption(_uc_expl)
            if _uc_delta_cap:
                st.caption(_uc_delta_cap)
            _uc_err = _uc_expl.get("load_error")
            if isinstance(_uc_err, str) and _uc_err.strip():
                st.warning(str(_uc_err))
            _uc_expl_rows = universal_critique_explainer_table_rows(_uc_expl)
            if _uc_expl_rows:
                _uc_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _uc_expl_slug = universal_critique_export_filename_slug()
                _uc_expl_json = universal_critique_explainer_export_json(_uc_expl)
                _uc_expl_csv = universal_critique_explainer_table_rows_csv(_uc_expl_rows)
                _uc_expl_dl_json_col, _uc_expl_dl_csv_col = st.columns(2)
                with _uc_expl_dl_json_col:
                    st.download_button(
                        label="Download universal critique explainer JSON",
                        data=_uc_expl_json.encode("utf-8"),
                        file_name=f"hermes_{_uc_expl_slug}_explainer_{_uc_expl_ts}.json",
                        mime="application/json",
                        key="hermes_dl_universal_critique_explainer_json",
                    )
                with _uc_expl_dl_csv_col:
                    if _uc_expl_csv:
                        st.download_button(
                            label="Download universal critique explainer CSV",
                            data=_uc_expl_csv.encode("utf-8"),
                            file_name=f"hermes_{_uc_expl_slug}_explainer_{_uc_expl_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_universal_critique_explainer_csv",
                        )
            with st.expander("Raw universal critique explainer JSON", expanded=False):
                st.json(_uc_expl)
            st.caption(
                "Optional **workflow vs timeline** table: paste the top-level "
                "``universal_critique`` object **or** full **GET /v1/runs/{id}/timeline** JSON. "
                "Workflow counts are from the selected profile YAML; timeline values are "
                "observed gate rollups. PLAN_GAP §14 #16."
            )
            _uc_tl_raw = st.text_area(
                "Optional timeline or universal_critique JSON",
                value="",
                height=100,
                key="hermes_universal_critique_timeline_compare_json",
                placeholder='{"fail_count": 0, "stage_count": 2, "stages": [...]} or full timeline',
            )
            _uc_tl_uc: dict[str, Any] | None = None
            if _uc_tl_raw.strip():
                try:
                    _uc_tl_parsed = json.loads(_uc_tl_raw)
                    if isinstance(_uc_tl_parsed, dict):
                        _uc_tl_uc = universal_critique_snapshot_from_compare_paste(
                            _uc_tl_parsed,
                        )
                    else:
                        st.warning(
                            "Timeline comparison JSON must be a single object (dict), "
                            "not a list or scalar.",
                        )
                except json.JSONDecodeError as exc:
                    st.warning(f"Invalid JSON ({exc.msg}).")
            _uc_compare_rows = universal_critique_workflow_vs_timeline_rows(
                _uc_expl,
                _uc_tl_uc,
            )
            st.dataframe(_uc_compare_rows, use_container_width=True, hide_index=True)
            with st.expander("Raw universal_critique vs pasted timeline JSON", expanded=False):
                st.json(
                    {
                        "workflow_explainer": _uc_expl,
                        "timeline_universal_critique": _uc_tl_uc,
                    },
                )
        with st.expander("Self-refinement (workflow + policy, fo135)", expanded=False):
            st.caption(
                "Read-only: workflow ``self_refinement`` from the **same** profile stem vs "
                "``configs/self_refinement/policy.yaml`` — **marker_merge** mirrors "
                "``_maybe_emit_self_refinement_stage_marker`` (emit when policy **or** workflow "
                "enables; version/description workflow wins when set). Env "
                "``HERMES_SELF_REFINEMENT_STAGE_MARKER`` in ``0``/``false``/``no`` suppresses "
                "the ``self_refinement:policy`` stage marker. PLAN_GAP §14 #17."
            )
            _sr_expl = self_refinement_workflow_explainer_payload(
                _iroot,
                workflow_profile=_wf_pick,
            )
            _sr_expl_metrics = self_refinement_workflow_explainer_operator_metrics(_sr_expl)
            _sr_expl_metrics_cap = self_refinement_workflow_explainer_operator_metrics_caption(
                _sr_expl_metrics,
            )
            if _sr_expl_metrics_cap:
                st.caption(_sr_expl_metrics_cap)
            _sr_expl_metric_rows = self_refinement_workflow_explainer_operator_metrics_table_rows(
                _sr_expl_metrics,
            )
            if _sr_expl_metric_rows:
                st.dataframe(_sr_expl_metric_rows, use_container_width=True, hide_index=True)
            _sr_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _sr_expl_metrics_slug = (
                self_refinement_workflow_explainer_operator_metrics_export_filename_slug()
            )
            _sr_expl_metrics_json = self_refinement_workflow_explainer_operator_metrics_export_json(
                _sr_expl_metrics,
            )
            _sr_expl_metrics_csv = (
                self_refinement_workflow_explainer_operator_metrics_table_rows_csv(
                    _sr_expl_metric_rows,
                )
            )
            _sr_expl_m_dl_json_col, _sr_expl_m_dl_csv_col = st.columns(2)
            with _sr_expl_m_dl_json_col:
                st.download_button(
                    label="Download self-refinement operator metrics JSON",
                    data=_sr_expl_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_sr_expl_metrics_slug}_{_sr_expl_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_self_refinement_explainer_metrics_json",
                )
            with _sr_expl_m_dl_csv_col:
                if _sr_expl_metrics_csv:
                    st.download_button(
                        label="Download self-refinement operator metrics CSV",
                        data=_sr_expl_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_sr_expl_metrics_slug}_{_sr_expl_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_self_refinement_explainer_metrics_csv",
                    )
            _sr_emit_cap = self_refinement_would_emit_marker_caption(
                _sr_expl.get("marker_merge"),
            )
            if _sr_emit_cap:
                st.caption(_sr_emit_cap)
            _sr_ver_cap = self_refinement_merged_version_caption(_sr_expl.get("marker_merge"))
            if _sr_ver_cap:
                st.caption(_sr_ver_cap)
            _sr_desc_cap = self_refinement_merged_description_preview_caption(
                _sr_expl.get("marker_merge"),
            )
            if _sr_desc_cap:
                st.caption(_sr_desc_cap)
            _sr_after_env_cap = self_refinement_would_emit_after_env_caption(
                _sr_expl.get("marker_merge"),
            )
            if _sr_after_env_cap:
                st.caption(_sr_after_env_cap)
            _sr_ungated_env_cap = self_refinement_ungated_loop_env_gate_caption(_sr_expl)
            if _sr_ungated_env_cap:
                st.caption(_sr_ungated_env_cap)
            _sr_disk_ver_cap = self_refinement_policy_yaml_disk_version_caption(_sr_expl)
            if _sr_disk_ver_cap:
                st.caption(_sr_disk_ver_cap)
            _sr_pol_bytes_cap = self_refinement_policy_yaml_file_bytes_caption(_sr_expl)
            if _sr_pol_bytes_cap:
                st.caption(_sr_pol_bytes_cap)
            _sr_raw_type_cap = self_refinement_workflow_yaml_raw_type_caption(_sr_expl)
            if _sr_raw_type_cap:
                st.caption(_sr_raw_type_cap)
            _sr_rows = [
                {
                    "field": "self_refinement block in workflow YAML",
                    "value": str(_sr_expl.get("self_refinement_yaml_present")),
                },
                {
                    "field": "self_refinement (raw value Python type)",
                    "value": "—"
                    if _sr_expl.get("self_refinement_workflow_yaml_raw_type") is None
                    else str(_sr_expl.get("self_refinement_workflow_yaml_raw_type")),
                },
                {
                    "field": "self_refinement (mapping string-key count in YAML)",
                    "value": "—"
                    if _sr_expl.get("self_refinement_yaml_mapping_string_key_count") is None
                    else str(_sr_expl.get("self_refinement_yaml_mapping_string_key_count")),
                },
                {
                    "field": "policy.yaml on-disk size (bytes)",
                    "value": "—"
                    if _sr_expl.get("policy_yaml", {}).get("policy_yaml_file_bytes") is None
                    else str(_sr_expl.get("policy_yaml", {}).get("policy_yaml_file_bytes")),
                },
                {
                    "field": "policy.yaml top-level version (int, disk)",
                    "value": "—"
                    if _sr_expl.get("policy_yaml", {}).get("policy_yaml_top_level_version_int")
                    is None
                    else str(
                        _sr_expl.get("policy_yaml", {}).get("policy_yaml_top_level_version_int"),
                    ),
                },
                {
                    "field": "policy.yaml description length (chars)",
                    "value": str(_sr_expl.get("policy_yaml", {}).get("description_char_len")),
                },
                {
                    "field": "workflow self_refinement.enabled",
                    "value": str(_sr_expl.get("workflow_self_refinement", {}).get("enabled")),
                },
                {
                    "field": "policy.yaml enabled (disk)",
                    "value": str(_sr_expl.get("policy_yaml", {}).get("enabled")),
                },
                {
                    "field": "would_emit self_refinement:policy marker",
                    "value": str(
                        _sr_expl.get("marker_merge", {}).get("would_emit_self_refinement_marker"),
                    ),
                },
                {
                    "field": "would_emit after env (effective)",
                    "value": str(
                        _sr_expl.get("marker_merge", {}).get("would_emit_marker_after_env"),
                    ),
                },
            ]
            st.dataframe(_sr_rows, use_container_width=True, hide_index=True)
            st.caption(
                "Optional **marker_merge vs timeline** table: paste either the top-level "
                "``self_refinement`` object **or** the full **GET /v1/runs/{id}/timeline** JSON "
                "(``events`` + summaries); the console extracts ``self_refinement`` when needed. "
                "Explainer values are predictive for the workflow profile above; timeline values "
                "are the last observed snapshot. When present, **``marker_count``** matches the "
                "timeline read-model (Run detail / API). PLAN_GAP §14 #17."
            )
            _sr_tl_raw = st.text_area(
                "Optional timeline or self_refinement JSON",
                value="",
                height=100,
                key="hermes_self_refinement_timeline_compare_json",
                placeholder='{"version": 1, "description": "…"} or full timeline JSON',
            )
            _sr_tl_sr: dict[str, Any] | None = None
            if _sr_tl_raw.strip():
                try:
                    _sr_tl_parsed = json.loads(_sr_tl_raw)
                    if isinstance(_sr_tl_parsed, dict):
                        _sr_tl_sr = self_refinement_snapshot_from_compare_paste(_sr_tl_parsed)
                    else:
                        st.warning(
                            "Timeline comparison JSON must be a single object (dict), "
                            "not a list or scalar.",
                        )
                except json.JSONDecodeError as exc:
                    st.warning(f"Invalid JSON ({exc.msg}).")
            _sr_compare_rows = self_refinement_marker_merge_vs_timeline_rows(
                _sr_expl.get("marker_merge"),
                _sr_tl_sr,
            )
            st.dataframe(_sr_compare_rows, use_container_width=True, hide_index=True)
            _sr_marker_merge = _sr_expl.get("marker_merge")
            if isinstance(_sr_marker_merge, dict):
                _sr_compare_snap = self_refinement_marker_merge_compare_snapshot(
                    _sr_marker_merge,
                    _sr_tl_sr,
                )
                _sr_compare_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _sr_compare_slug = self_refinement_marker_merge_compare_export_filename_slug()
                _sr_compare_json = self_refinement_marker_merge_compare_export_json(
                    _sr_compare_snap,
                )
                _sr_compare_csv = self_refinement_marker_merge_compare_table_rows_csv(
                    _sr_compare_rows,
                )
                _sr_compare_dl_json_col, _sr_compare_dl_csv_col = st.columns(2)
                with _sr_compare_dl_json_col:
                    st.download_button(
                        label="Download marker compare JSON",
                        data=_sr_compare_json.encode("utf-8"),
                        file_name=f"hermes_{_sr_compare_slug}_{_sr_compare_ts}.json",
                        mime="application/json",
                        key="hermes_dl_self_refinement_marker_compare_json",
                    )
                with _sr_compare_dl_csv_col:
                    if _sr_compare_csv:
                        st.download_button(
                            label="Download marker compare CSV",
                            data=_sr_compare_csv.encode("utf-8"),
                            file_name=f"hermes_{_sr_compare_slug}_{_sr_compare_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_self_refinement_marker_compare_csv",
                        )
            with st.expander("Raw marker_merge vs pasted timeline JSON", expanded=False):
                st.json(
                    {
                        "marker_merge": _sr_expl.get("marker_merge"),
                        "timeline_self_refinement": _sr_tl_sr,
                    },
                )
            _sr_err = _sr_expl.get("load_error")
            if isinstance(_sr_err, str) and _sr_err.strip():
                st.warning(str(_sr_err))
            _sr_expl_rows = self_refinement_explainer_table_rows(_sr_expl)
            if _sr_expl_rows:
                _sr_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _sr_expl_slug = self_refinement_export_filename_slug()
                _sr_expl_json = self_refinement_explainer_export_json(_sr_expl)
                _sr_expl_csv = self_refinement_explainer_table_rows_csv(_sr_expl_rows)
                _sr_expl_dl_json_col, _sr_expl_dl_csv_col = st.columns(2)
                with _sr_expl_dl_json_col:
                    st.download_button(
                        label="Download self-refinement explainer JSON",
                        data=_sr_expl_json.encode("utf-8"),
                        file_name=f"hermes_{_sr_expl_slug}_explainer_{_sr_expl_ts}.json",
                        mime="application/json",
                        key="hermes_dl_self_refinement_explainer_json",
                    )
                with _sr_expl_dl_csv_col:
                    if _sr_expl_csv:
                        st.download_button(
                            label="Download self-refinement explainer CSV",
                            data=_sr_expl_csv.encode("utf-8"),
                            file_name=f"hermes_{_sr_expl_slug}_explainer_{_sr_expl_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_self_refinement_explainer_csv",
                        )
            with st.expander("Raw self-refinement explainer JSON", expanded=False):
                st.json(_sr_expl)
        with st.expander("Security scan metadata on verify (workflow + env, fo136)", expanded=False):
            st.caption(
                "Read-only: ``security_scan_metadata_on_verify`` from the **same** workflow profile vs "
                "``HERMES_ATTACH_SECURITY_SCAN_METADATA`` — **yaml_parsed_bool** is frozen YAML only; "
                "**effective_enabled** matches ``security_scan_metadata_on_verify_enabled`` "
                "(truthy env forces on; ``0`` / ``false`` / ``no`` kill-switch). PLAN_GAP §14 #18."
            )
            _ssm_expl = security_scan_metadata_workflow_explainer_payload(
                _iroot,
                workflow_profile=_wf_pick,
            )
            _ssm_expl_metrics = security_scan_metadata_workflow_explainer_operator_metrics(
                _ssm_expl,
            )
            _ssm_expl_metrics_cap = (
                security_scan_metadata_workflow_explainer_operator_metrics_caption(
                    _ssm_expl_metrics,
                )
            )
            if _ssm_expl_metrics_cap:
                st.caption(_ssm_expl_metrics_cap)
            _ssm_expl_metric_rows = (
                security_scan_metadata_workflow_explainer_operator_metrics_table_rows(
                    _ssm_expl_metrics,
                )
            )
            if _ssm_expl_metric_rows:
                st.dataframe(_ssm_expl_metric_rows, use_container_width=True, hide_index=True)
            _ssm_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ssm_expl_metrics_slug = (
                security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug()
            )
            _ssm_expl_metrics_json = (
                security_scan_metadata_workflow_explainer_operator_metrics_export_json(
                    _ssm_expl_metrics,
                )
            )
            _ssm_expl_metrics_csv = (
                security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv(
                    _ssm_expl_metric_rows,
                )
            )
            _ssm_expl_m_dl_json_col, _ssm_expl_m_dl_csv_col = st.columns(2)
            with _ssm_expl_m_dl_json_col:
                st.download_button(
                    label="Download security scan metadata operator metrics JSON",
                    data=_ssm_expl_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_ssm_expl_metrics_slug}_{_ssm_expl_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_security_scan_metadata_explainer_metrics_json",
                )
            with _ssm_expl_m_dl_csv_col:
                if _ssm_expl_metrics_csv:
                    st.download_button(
                        label="Download security scan metadata operator metrics CSV",
                        data=_ssm_expl_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_ssm_expl_metrics_slug}_{_ssm_expl_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_security_scan_metadata_explainer_metrics_csv",
                    )
            _ssm_env = _ssm_expl.get("HERMES_ATTACH_SECURITY_SCAN_METADATA")
            _ssm_env_raw = ""
            if isinstance(_ssm_env, dict):
                _ssm_env_raw = str(_ssm_env.get("raw", ""))
            _ssm_yaml_val = _ssm_expl.get("security_scan_metadata_on_verify_yaml_value")
            _ssm_rows = [
                {
                    "field": "workflow YAML top-level version (int)",
                    "value": "—"
                    if _ssm_expl.get("workflow_yaml_top_level_version_int") is None
                    else str(_ssm_expl.get("workflow_yaml_top_level_version_int")),
                },
                {
                    "field": "workflow YAML top-level string key count",
                    "value": "—"
                    if _ssm_expl.get("workflow_yaml_top_level_string_key_count") is None
                    else str(_ssm_expl.get("workflow_yaml_top_level_string_key_count")),
                },
                {
                    "field": "workflow YAML file size (bytes, on disk)",
                    "value": "—"
                    if _ssm_expl.get("workflow_yaml_file_bytes") is None
                    else str(_ssm_expl.get("workflow_yaml_file_bytes")),
                },
                {
                    "field": "security_scan_metadata_on_verify key in YAML",
                    "value": str(_ssm_expl.get("security_scan_metadata_on_verify_yaml_key_present")),
                },
                {
                    "field": "security_scan_metadata_on_verify (raw value)",
                    "value": "—" if _ssm_yaml_val is None else repr(_ssm_yaml_val),
                },
                {
                    "field": "security_scan_metadata_on_verify (raw value Python type)",
                    "value": "—"
                    if _ssm_expl.get("security_scan_metadata_on_verify_yaml_raw_type") is None
                    else str(_ssm_expl.get("security_scan_metadata_on_verify_yaml_raw_type")),
                },
                {
                    "field": "security_scan_metadata_on_verify (mapping string-key count)",
                    "value": "—"
                    if _ssm_expl.get("security_scan_metadata_on_verify_mapping_string_key_count")
                    is None
                    else str(
                        _ssm_expl.get("security_scan_metadata_on_verify_mapping_string_key_count"),
                    ),
                },
                {
                    "field": "yaml_parsed_bool (workflow file only)",
                    "value": str(_ssm_expl.get("yaml_parsed_bool")),
                },
                {
                    "field": "HERMES_ATTACH_SECURITY_SCAN_METADATA (raw)",
                    "value": _ssm_env_raw if _ssm_env_raw else "(unset)",
                },
                {
                    "field": "effective_enabled (YAML + env)",
                    "value": str(_ssm_expl.get("effective_enabled")),
                },
                {
                    "field": "yaml_parsed_bool matches effective_enabled",
                    "value": str(
                        _ssm_expl.get("security_scan_metadata_yaml_parsed_bool_matches_effective"),
                    ),
                },
            ]
            st.dataframe(_ssm_rows, use_container_width=True, hide_index=True)
            _ssm_relpath_cap = security_scan_metadata_workflow_yaml_relpath_caption(_ssm_expl)
            if _ssm_relpath_cap:
                st.caption(_ssm_relpath_cap)
            _ssm_bytes_cap = security_scan_metadata_workflow_yaml_file_bytes_caption(_ssm_expl)
            if _ssm_bytes_cap:
                st.caption(_ssm_bytes_cap)
            _ssm_version_cap = security_scan_metadata_workflow_yaml_version_caption(_ssm_expl)
            if _ssm_version_cap:
                st.caption(_ssm_version_cap)
            _ssm_str_keys_cap = security_scan_metadata_workflow_yaml_string_key_count_caption(
                _ssm_expl,
            )
            if _ssm_str_keys_cap:
                st.caption(_ssm_str_keys_cap)
            _ssm_raw_type_cap = security_scan_metadata_yaml_raw_type_caption(_ssm_expl)
            if _ssm_raw_type_cap:
                st.caption(_ssm_raw_type_cap)
            _ssm_eff_cap = security_scan_metadata_effective_enabled_caption(_ssm_expl)
            if _ssm_eff_cap:
                st.caption(_ssm_eff_cap)
            _ssm_env_cap = security_scan_metadata_env_gate_caption(_ssm_expl)
            if _ssm_env_cap:
                st.caption(_ssm_env_cap)
            _ssm_map_cap = security_scan_metadata_mapping_key_count_caption(_ssm_expl)
            if _ssm_map_cap:
                st.caption(_ssm_map_cap)
            _ssm_mis_cap = security_scan_metadata_yaml_effective_mismatch_caption(_ssm_expl)
            if _ssm_mis_cap:
                st.caption(_ssm_mis_cap)
            _ssm_err = _ssm_expl.get("load_error")
            if isinstance(_ssm_err, str) and _ssm_err.strip():
                st.warning(str(_ssm_err))
            _ssm_expl_rows = security_scan_metadata_explainer_table_rows(_ssm_expl)
            if _ssm_expl_rows:
                _ssm_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _ssm_expl_slug = security_scan_metadata_export_filename_slug()
                _ssm_expl_json = security_scan_metadata_explainer_export_json(_ssm_expl)
                _ssm_expl_csv = security_scan_metadata_explainer_table_rows_csv(_ssm_expl_rows)
                _ssm_expl_dl_json_col, _ssm_expl_dl_csv_col = st.columns(2)
                with _ssm_expl_dl_json_col:
                    st.download_button(
                        label="Download security scan metadata explainer JSON",
                        data=_ssm_expl_json.encode("utf-8"),
                        file_name=f"hermes_{_ssm_expl_slug}_explainer_{_ssm_expl_ts}.json",
                        mime="application/json",
                        key="hermes_dl_security_scan_metadata_explainer_json",
                    )
                with _ssm_expl_dl_csv_col:
                    if _ssm_expl_csv:
                        st.download_button(
                            label="Download security scan metadata explainer CSV",
                            data=_ssm_expl_csv.encode("utf-8"),
                            file_name=f"hermes_{_ssm_expl_slug}_explainer_{_ssm_expl_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_security_scan_metadata_explainer_csv",
                        )
            with st.expander("Raw security scan metadata explainer JSON", expanded=False):
                st.json(_ssm_expl)
        with st.expander("Escalation suppress (workflow YAML, fo137)", expanded=False):
            st.caption(
                "Read-only: ``escalation.suppress_automatic_escalation`` from the **same** profile "
                "stem — **suppress_automatic_escalation_effective** matches "
                "``parse_escalation_workflow_block`` (same boolean the pipeline uses in "
                "``_workflow_suppresses_automatic_escalation`` once the run profile resolves to "
                "this stem). Non-dict ``escalation:`` collapses to off. PLAN_GAP §14 #19."
            )
            _es_expl = escalation_suppress_workflow_explainer_payload(
                _iroot,
                workflow_profile=_wf_pick,
            )
            _es_expl_metrics = escalation_suppress_workflow_explainer_operator_metrics(_es_expl)
            _es_expl_metrics_cap = escalation_suppress_workflow_explainer_operator_metrics_caption(
                _es_expl_metrics,
            )
            if _es_expl_metrics_cap:
                st.caption(_es_expl_metrics_cap)
            _es_expl_metric_rows = (
                escalation_suppress_workflow_explainer_operator_metrics_table_rows(
                    _es_expl_metrics,
                )
            )
            if _es_expl_metric_rows:
                st.dataframe(_es_expl_metric_rows, use_container_width=True, hide_index=True)
            _es_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _es_expl_metrics_slug = (
                escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug()
            )
            _es_expl_metrics_json = (
                escalation_suppress_workflow_explainer_operator_metrics_export_json(
                    _es_expl_metrics,
                )
            )
            _es_expl_metrics_csv = (
                escalation_suppress_workflow_explainer_operator_metrics_table_rows_csv(
                    _es_expl_metric_rows,
                )
            )
            _es_expl_m_dl_json_col, _es_expl_m_dl_csv_col = st.columns(2)
            with _es_expl_m_dl_json_col:
                st.download_button(
                    label="Download escalation suppress operator metrics JSON",
                    data=_es_expl_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_es_expl_metrics_slug}_{_es_expl_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_escalation_suppress_explainer_metrics_json",
                )
            with _es_expl_m_dl_csv_col:
                if _es_expl_metrics_csv:
                    st.download_button(
                        label="Download escalation suppress operator metrics CSV",
                        data=_es_expl_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_es_expl_metrics_slug}_{_es_expl_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_escalation_suppress_explainer_metrics_csv",
                    )
            _sup_raw = _es_expl.get("suppress_automatic_escalation_yaml_raw")
            _pol_keys = _es_expl.get("escalation_policy_yaml_top_level_keys_sample")
            _pol_keys_s = (
                "—"
                if not isinstance(_pol_keys, list) or not _pol_keys
                else ", ".join(str(x) for x in _pol_keys)
            )
            _es_rows = [
                {
                    "field": "workflow YAML top-level version (int)",
                    "value": "—"
                    if _es_expl.get("workflow_yaml_top_level_version_int") is None
                    else str(_es_expl.get("workflow_yaml_top_level_version_int")),
                },
                {
                    "field": "configs/escalation/policy.yaml (on disk)",
                    "value": str(_es_expl.get("escalation_policy_yaml_path_exists")),
                },
                {
                    "field": "escalation policy YAML (repo-relative)",
                    "value": "—"
                    if not _es_expl.get("escalation_policy_yaml_relpath")
                    else str(_es_expl.get("escalation_policy_yaml_relpath")),
                },
                {
                    "field": "escalation policy YAML on-disk size (bytes)",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_file_bytes") is None
                    else str(_es_expl.get("escalation_policy_yaml_file_bytes")),
                },
                {
                    "field": "escalation policy top-level key count",
                    "value": str(_es_expl.get("escalation_policy_yaml_top_level_key_count")),
                },
                {
                    "field": "escalation policy top-level keys (sample, max 12)",
                    "value": _pol_keys_s,
                },
                {
                    "field": "policy.yaml has top-level verification mapping",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_has_verification_mapping") is None
                    else str(_es_expl.get("escalation_policy_yaml_has_verification_mapping")),
                },
                {
                    "field": "policy.yaml has top-level anti_deadlock mapping",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_has_anti_deadlock_mapping") is None
                    else str(_es_expl.get("escalation_policy_yaml_has_anti_deadlock_mapping")),
                },
                {
                    "field": "policy.yaml max_retries_per_stage (int)",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_max_retries_per_stage") is None
                    else str(_es_expl.get("escalation_policy_yaml_max_retries_per_stage")),
                },
                {
                    "field": "policy.yaml deadlock_escalation_after_minutes (int)",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_deadlock_escalation_after_minutes")
                    is None
                    else str(
                        _es_expl.get("escalation_policy_yaml_deadlock_escalation_after_minutes"),
                    ),
                },
                {
                    "field": "policy.yaml version (int)",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_version") is None
                    else str(_es_expl.get("escalation_policy_yaml_version")),
                },
                {
                    "field": "policy.yaml anti_deadlock.enabled (bool)",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_anti_deadlock_enabled") is None
                    else str(_es_expl.get("escalation_policy_yaml_anti_deadlock_enabled")),
                },
                {
                    "field": "policy.yaml anti_deadlock.min_progress_events (int)",
                    "value": "—"
                    if _es_expl.get("escalation_policy_yaml_anti_deadlock_min_progress_events")
                    is None
                    else str(
                        _es_expl.get("escalation_policy_yaml_anti_deadlock_min_progress_events"),
                    ),
                },
                {
                    "field": "escalation key in YAML",
                    "value": str(_es_expl.get("escalation_yaml_key_present")),
                },
                {
                    "field": "escalation block (snapshot)",
                    "value": "—"
                    if _es_expl.get("escalation_yaml_value") is None
                    else repr(_es_expl.get("escalation_yaml_value")),
                },
                {
                    "field": "suppress_automatic_escalation (raw in block)",
                    "value": "—" if _sup_raw is None else repr(_sup_raw),
                },
                {
                    "field": "suppress_automatic_escalation raw JSON type",
                    "value": "—"
                    if _es_expl.get("suppress_automatic_escalation_yaml_raw_type") is None
                    else str(_es_expl.get("suppress_automatic_escalation_yaml_raw_type")),
                },
                {
                    "field": "suppress_automatic_escalation_effective",
                    "value": str(_es_expl.get("suppress_automatic_escalation_effective")),
                },
            ]
            st.dataframe(_es_rows, use_container_width=True, hide_index=True)
            _es_yaml_key_cap = escalation_yaml_key_present_caption(_es_expl)
            if _es_yaml_key_cap:
                st.caption(_es_yaml_key_cap)
            _es_kinds_caption = escalation_policy_yaml_top_level_kinds_caption(_es_expl)
            if _es_kinds_caption:
                st.caption(_es_kinds_caption)
            _es_kinds_rows = escalation_policy_yaml_top_level_kinds_table_rows(_es_expl)
            if _es_kinds_rows:
                _es_kinds_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _es_kinds_slug = escalation_policy_export_filename_slug()
                _es_kinds_json = escalation_policy_yaml_top_level_kinds_export_json(
                    _es_kinds_rows,
                )
                _es_kinds_csv = escalation_policy_yaml_top_level_kinds_table_rows_csv(
                    _es_kinds_rows,
                )
                _es_kinds_dl_json_col, _es_kinds_dl_csv_col = st.columns(2)
                with _es_kinds_dl_json_col:
                    st.download_button(
                        label="Download escalation policy kinds JSON",
                        data=_es_kinds_json.encode("utf-8"),
                        file_name=f"hermes_{_es_kinds_slug}_kinds_{_es_kinds_ts}.json",
                        mime="application/json",
                        key="hermes_dl_escalation_policy_kinds_json",
                    )
                with _es_kinds_dl_csv_col:
                    if _es_kinds_csv:
                        st.download_button(
                            label="Download escalation policy kinds CSV",
                            data=_es_kinds_csv.encode("utf-8"),
                            file_name=f"hermes_{_es_kinds_slug}_kinds_{_es_kinds_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_escalation_policy_kinds_csv",
                        )
            _es_ver_shape = escalation_policy_yaml_verification_shape_caption(_es_expl)
            if _es_ver_shape:
                st.caption(_es_ver_shape)
            _es_ad_shape = escalation_policy_yaml_anti_deadlock_shape_caption(_es_expl)
            if _es_ad_shape:
                st.caption(_es_ad_shape)
            _es_deadlock_min_cap = escalation_policy_yaml_deadlock_minutes_caption(_es_expl)
            if _es_deadlock_min_cap:
                st.caption(_es_deadlock_min_cap)
            _es_ad_min_progress_cap = escalation_policy_yaml_anti_deadlock_min_progress_caption(
                _es_expl,
            )
            if _es_ad_min_progress_cap:
                st.caption(_es_ad_min_progress_cap)
            _es_key_count_caption = escalation_policy_yaml_key_count_caption(_es_expl)
            if _es_key_count_caption:
                st.caption(_es_key_count_caption)
            _es_policy_ver_cap = escalation_policy_yaml_version_caption(_es_expl)
            if _es_policy_ver_cap:
                st.caption(_es_policy_ver_cap)
            _es_max_retries_cap = escalation_policy_yaml_max_retries_caption(_es_expl)
            if _es_max_retries_cap:
                st.caption(_es_max_retries_cap)
            _es_keys_sample_caption = escalation_policy_yaml_keys_sample_caption(_es_expl)
            if _es_keys_sample_caption:
                st.caption(_es_keys_sample_caption)
            _es_key_count = _es_expl.get("escalation_policy_yaml_top_level_key_count")
            _es_keys_all_rows = escalation_policy_yaml_keys_all_table_rows(_es_expl)
            if (
                _es_keys_all_rows
                and type(_es_key_count) is int
                and _es_key_count > 12
            ):
                _es_keys_all_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _es_keys_all_slug = escalation_policy_export_filename_slug()
                _es_keys_all_json = escalation_policy_yaml_keys_all_export_json(
                    _es_keys_all_rows,
                )
                _es_keys_all_csv = escalation_policy_yaml_keys_all_table_rows_csv(
                    _es_keys_all_rows,
                )
                _es_keys_all_dl_json_col, _es_keys_all_dl_csv_col = st.columns(2)
                with _es_keys_all_dl_json_col:
                    st.download_button(
                        label="Download escalation policy keys (full) JSON",
                        data=_es_keys_all_json.encode("utf-8"),
                        file_name=(
                            f"hermes_{_es_keys_all_slug}_keys_full_{_es_keys_all_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_escalation_policy_keys_full_json",
                    )
                with _es_keys_all_dl_csv_col:
                    if _es_keys_all_csv:
                        st.download_button(
                            label="Download escalation policy keys (full) CSV",
                            data=_es_keys_all_csv.encode("utf-8"),
                            file_name=(
                                f"hermes_{_es_keys_all_slug}_keys_full_{_es_keys_all_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_escalation_policy_keys_full_csv",
                        )
            _es_relpath_caption = escalation_policy_yaml_relpath_caption(_es_expl)
            if _es_relpath_caption:
                st.caption(_es_relpath_caption)
            _es_mtime_caption = escalation_policy_yaml_mtime_caption(_es_expl)
            if _es_mtime_caption:
                st.caption(_es_mtime_caption)
            _es_age_cap = escalation_policy_yaml_age_caption(_es_expl)
            if _es_age_cap:
                st.caption(_es_age_cap)
            _es_pol_bytes_cap = escalation_policy_yaml_file_bytes_caption(_es_expl)
            if _es_pol_bytes_cap:
                st.caption(_es_pol_bytes_cap)
            _es_flag_caption = escalation_suppress_flag_caption(_es_expl)
            if _es_flag_caption:
                st.caption(_es_flag_caption)
            _es_err = _es_expl.get("load_error")
            if isinstance(_es_err, str) and _es_err.strip():
                st.warning(str(_es_err))
            _es_pol_err = _es_expl.get("escalation_policy_yaml_load_error")
            if isinstance(_es_pol_err, str) and _es_pol_err.strip():
                st.warning(
                    "``configs/escalation/policy.yaml`` failed to parse: " + str(_es_pol_err),
                )
            _es_expl_rows = escalation_suppress_explainer_table_rows(_es_expl)
            if _es_expl_rows:
                _es_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _es_expl_slug = escalation_suppress_export_filename_slug()
                _es_expl_json = escalation_suppress_explainer_export_json(_es_expl)
                _es_expl_csv = escalation_suppress_explainer_table_rows_csv(_es_expl_rows)
                _es_expl_dl_json_col, _es_expl_dl_csv_col = st.columns(2)
                with _es_expl_dl_json_col:
                    st.download_button(
                        label="Download escalation suppress explainer JSON",
                        data=_es_expl_json.encode("utf-8"),
                        file_name=f"hermes_{_es_expl_slug}_explainer_{_es_expl_ts}.json",
                        mime="application/json",
                        key="hermes_dl_escalation_suppress_explainer_json",
                    )
                with _es_expl_dl_csv_col:
                    if _es_expl_csv:
                        st.download_button(
                            label="Download escalation suppress explainer CSV",
                            data=_es_expl_csv.encode("utf-8"),
                            file_name=f"hermes_{_es_expl_slug}_explainer_{_es_expl_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_escalation_suppress_explainer_csv",
                        )
            with st.expander("Raw escalation suppress explainer JSON", expanded=False):
                st.json(_es_expl)
        with st.expander("Agent evaluator (workflow + env, fo139)", expanded=False):
            st.caption(
                "Read-only: ``agent_evaluator`` from the **same** profile stem vs "
                "``HERMES_AGENT_EVALUATOR`` — **yaml_parsed_*** is frozen YAML; "
                "**would_emit_stage_started** matches ``_maybe_emit_agent_evaluator_stage`` "
                "before create-run persona checks (kill-switch ``0``/``false``/``no``; "
                "``1``/``true``/``yes`` forces on). **persona_id** is always from the parsed "
                "workflow block when a stage would emit. PLAN_GAP §14 #15."
            )
            _ae_expl = agent_evaluator_workflow_explainer_payload(
                _iroot,
                workflow_profile=_wf_pick,
            )
            _ae_expl_metrics = agent_evaluator_workflow_explainer_operator_metrics(_ae_expl)
            _ae_expl_metrics_cap = agent_evaluator_workflow_explainer_operator_metrics_caption(
                _ae_expl_metrics,
            )
            if _ae_expl_metrics_cap:
                st.caption(_ae_expl_metrics_cap)
            _ae_expl_metric_rows = (
                agent_evaluator_workflow_explainer_operator_metrics_table_rows(_ae_expl_metrics)
            )
            if _ae_expl_metric_rows:
                st.dataframe(_ae_expl_metric_rows, use_container_width=True, hide_index=True)
            _ae_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _ae_expl_metrics_slug = (
                agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug()
            )
            _ae_expl_metrics_json = (
                agent_evaluator_workflow_explainer_operator_metrics_export_json(_ae_expl_metrics)
            )
            _ae_expl_metrics_csv = (
                agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv(
                    _ae_expl_metric_rows,
                )
            )
            _ae_expl_m_dl_json_col, _ae_expl_m_dl_csv_col = st.columns(2)
            with _ae_expl_m_dl_json_col:
                st.download_button(
                    label="Download agent evaluator operator metrics JSON",
                    data=_ae_expl_metrics_json.encode("utf-8"),
                    file_name=(
                        f"hermes_{_ae_expl_metrics_slug}_{_ae_expl_metrics_ts}.json"
                    ),
                    mime="application/json",
                    key="hermes_dl_agent_evaluator_explainer_metrics_json",
                )
            with _ae_expl_m_dl_csv_col:
                if _ae_expl_metrics_csv:
                    st.download_button(
                        label="Download agent evaluator operator metrics CSV",
                        data=_ae_expl_metrics_csv.encode("utf-8"),
                        file_name=(
                            f"hermes_{_ae_expl_metrics_slug}_{_ae_expl_metrics_ts}.csv"
                        ),
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_agent_evaluator_explainer_metrics_csv",
                    )
            _ae_env = _ae_expl.get("HERMES_AGENT_EVALUATOR")
            _ae_env_raw = ""
            if isinstance(_ae_env, dict):
                _ae_env_raw = str(_ae_env.get("raw", ""))
            _ae_yaml = _ae_expl.get("agent_evaluator_yaml_value")
            _ae_rows = [
                {
                    "field": "workflow YAML top-level version (int)",
                    "value": "—"
                    if _ae_expl.get("workflow_yaml_top_level_version_int") is None
                    else str(_ae_expl.get("workflow_yaml_top_level_version_int")),
                },
                {
                    "field": "agent_evaluator key in YAML",
                    "value": str(_ae_expl.get("agent_evaluator_yaml_key_present")),
                },
                {
                    "field": "agent_evaluator block (snapshot)",
                    "value": "—" if _ae_yaml is None else repr(_ae_yaml),
                },
                {
                    "field": "agent_evaluator (raw value Python type)",
                    "value": "—"
                    if _ae_expl.get("agent_evaluator_yaml_raw_type") is None
                    else str(_ae_expl.get("agent_evaluator_yaml_raw_type")),
                },
                {
                    "field": "agent_evaluator (mapping string-key count)",
                    "value": "—"
                    if _ae_expl.get("agent_evaluator_yaml_mapping_string_key_count") is None
                    else str(_ae_expl.get("agent_evaluator_yaml_mapping_string_key_count")),
                },
                {
                    "field": "agent_evaluator (top-level True bool values)",
                    "value": "—"
                    if _ae_expl.get("agent_evaluator_yaml_true_bool_value_count") is None
                    else str(_ae_expl.get("agent_evaluator_yaml_true_bool_value_count")),
                },
                {
                    "field": "agent_evaluator (top-level False bool values)",
                    "value": "—"
                    if _ae_expl.get("agent_evaluator_yaml_false_bool_value_count") is None
                    else str(_ae_expl.get("agent_evaluator_yaml_false_bool_value_count")),
                },
                {
                    "field": "yaml_parsed_enabled",
                    "value": str(_ae_expl.get("yaml_parsed_enabled")),
                },
                {
                    "field": "yaml_parsed_persona_id",
                    "value": str(_ae_expl.get("yaml_parsed_persona_id")),
                },
                {
                    "field": "HERMES_AGENT_EVALUATOR (raw)",
                    "value": _ae_env_raw if _ae_env_raw else "(unset)",
                },
                {
                    "field": "would_emit_stage_started (env + YAML gate)",
                    "value": str(_ae_expl.get("would_emit_stage_started")),
                },
            ]
            st.dataframe(_ae_rows, use_container_width=True, hide_index=True)
            _ae_env_cap = agent_evaluator_env_gate_caption(_ae_expl)
            if _ae_env_cap:
                st.caption(_ae_env_cap)
            _ae_wf_ver_cap = agent_evaluator_workflow_yaml_version_caption(_ae_expl)
            if _ae_wf_ver_cap:
                st.caption(_ae_wf_ver_cap)
            _ae_raw_type_cap = agent_evaluator_yaml_raw_type_caption(_ae_expl)
            if _ae_raw_type_cap:
                st.caption(_ae_raw_type_cap)
            _ae_true_bool_cap = agent_evaluator_yaml_true_bool_count_caption(_ae_expl)
            if _ae_true_bool_cap:
                st.caption(_ae_true_bool_cap)
            _ae_promote_cap = agent_evaluator_auto_promote_env_gate_caption(_ae_expl)
            if _ae_promote_cap:
                st.caption(_ae_promote_cap)
            _ae_create_cap = agent_evaluator_auto_create_env_gate_caption(_ae_expl)
            if _ae_create_cap:
                st.caption(_ae_create_cap)
            _ae_yaml_key_cap = agent_evaluator_yaml_key_present_caption(_ae_expl)
            if _ae_yaml_key_cap:
                st.caption(_ae_yaml_key_cap)
            _ae_persona_cap = agent_evaluator_persona_id_caption(_ae_expl)
            if _ae_persona_cap:
                st.caption(_ae_persona_cap)
            _ae_enabled_cap = agent_evaluator_yaml_parsed_enabled_caption(_ae_expl)
            if _ae_enabled_cap:
                st.caption(_ae_enabled_cap)
            _ae_llm_cap = agent_evaluator_llm_evaluation_enabled_caption(_ae_expl)
            if _ae_llm_cap:
                st.caption(_ae_llm_cap)
            _ae_would_cap = agent_evaluator_would_emit_caption(_ae_expl)
            if _ae_would_cap:
                st.caption(_ae_would_cap)
            _ae_err = _ae_expl.get("load_error")
            if isinstance(_ae_err, str) and _ae_err.strip():
                st.warning(str(_ae_err))
            _ae_expl_rows = agent_evaluator_explainer_table_rows(_ae_expl)
            if _ae_expl_rows:
                _ae_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _ae_expl_slug = agent_evaluator_export_filename_slug()
                _ae_expl_json = agent_evaluator_explainer_export_json(_ae_expl)
                _ae_expl_csv = agent_evaluator_explainer_table_rows_csv(_ae_expl_rows)
                _ae_expl_dl_json_col, _ae_expl_dl_csv_col = st.columns(2)
                with _ae_expl_dl_json_col:
                    st.download_button(
                        label="Download agent evaluator explainer JSON",
                        data=_ae_expl_json.encode("utf-8"),
                        file_name=f"hermes_{_ae_expl_slug}_explainer_{_ae_expl_ts}.json",
                        mime="application/json",
                        key="hermes_dl_agent_evaluator_explainer_json",
                    )
                with _ae_expl_dl_csv_col:
                    if _ae_expl_csv:
                        st.download_button(
                            label="Download agent evaluator explainer CSV",
                            data=_ae_expl_csv.encode("utf-8"),
                            file_name=f"hermes_{_ae_expl_slug}_explainer_{_ae_expl_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_agent_evaluator_explainer_csv",
                        )
            with st.expander("Raw agent evaluator explainer JSON", expanded=False):
                st.json(_ae_expl)
        st.text_area(
            "Optional pasted ``integrator_gate`` YAML (full workflow with key, or flat mapping)",
            height=120,
            placeholder="integrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n",
            key="hermes_integrator_paste_yaml",
        )
        with st.expander("Integrator thresholds & gate emission (fo133)", expanded=False):
            st.caption(
                "Read-only: **pipeline** ``min_score_to_pass`` resolution (matches gate emission) vs "
                "**Streamlit preview** (pasted fragment can change preview only), plus whether a "
                "``gate.decision.emitted`` would be written given ``HERMES_EMIT_INTEGRATOR_GATE``, "
                "``configs/integrator/thresholds.yaml`` **enabled**, and workflow "
                "``integrator_gate.enabled``."
            )
            _thr_payload = integrator_threshold_explainer_payload(
                _iroot,
                workflow_profile=_wf_pick,
                pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
            )
            _thr_expl_metrics = integrator_threshold_explainer_operator_metrics(_thr_payload)
            _thr_expl_metrics_cap = integrator_threshold_explainer_operator_metrics_caption(
                _thr_expl_metrics,
            )
            if _thr_expl_metrics_cap:
                st.caption(_thr_expl_metrics_cap)
            _thr_expl_metric_rows = integrator_threshold_explainer_operator_metrics_table_rows(
                _thr_expl_metrics,
            )
            if _thr_expl_metric_rows:
                st.dataframe(_thr_expl_metric_rows, use_container_width=True, hide_index=True)
            _thr_expl_metrics_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            _thr_expl_metrics_slug = (
                integrator_threshold_explainer_operator_metrics_export_filename_slug()
            )
            _thr_expl_metrics_json = integrator_threshold_explainer_operator_metrics_export_json(
                _thr_expl_metrics,
            )
            _thr_expl_metrics_csv = (
                integrator_threshold_explainer_operator_metrics_table_rows_csv(
                    _thr_expl_metric_rows,
                )
            )
            _thr_expl_m_dl_json_col, _thr_expl_m_dl_csv_col = st.columns(2)
            with _thr_expl_m_dl_json_col:
                st.download_button(
                    label="Download integrator threshold operator metrics JSON",
                    data=_thr_expl_metrics_json.encode("utf-8"),
                    file_name=f"hermes_{_thr_expl_metrics_slug}_{_thr_expl_metrics_ts}.json",
                    mime="application/json",
                    key="hermes_dl_integrator_threshold_explainer_metrics_json",
                )
            with _thr_expl_m_dl_csv_col:
                if _thr_expl_metrics_csv:
                    st.download_button(
                        label="Download integrator threshold operator metrics CSV",
                        data=_thr_expl_metrics_csv.encode("utf-8"),
                        file_name=f"hermes_{_thr_expl_metrics_slug}_{_thr_expl_metrics_ts}.csv",
                        mime="text/csv; charset=utf-8",
                        key="hermes_dl_integrator_threshold_explainer_metrics_csv",
                    )
            _thr_emit_cap = integrator_threshold_gate_emission_caption(_thr_payload)
            if _thr_emit_cap:
                st.caption(_thr_emit_cap)
            _thr_min_cap = integrator_threshold_min_score_agreement_caption(_thr_payload)
            if _thr_min_cap:
                st.caption(_thr_min_cap)
            _thr_tags_cap = integrator_threshold_project_tags_caption(_thr_payload)
            if _thr_tags_cap:
                st.caption(_thr_tags_cap)
            _thr_paste_cap = integrator_threshold_paste_parse_caption(_thr_payload)
            if _thr_paste_cap:
                st.caption(_thr_paste_cap)
            _thr_thr_ver_cap = integrator_threshold_thresholds_yaml_version_caption(
                _thr_payload,
            )
            if _thr_thr_ver_cap:
                st.caption(_thr_thr_ver_cap)
            _thr_ty = _thr_payload.get("thresholds_yaml")
            _thr_ver = (
                "—"
                if not isinstance(_thr_ty, dict)
                or _thr_ty.get("top_level_version_int") is None
                else str(_thr_ty.get("top_level_version_int"))
            )
            _thr_bytes = (
                "—"
                if not isinstance(_thr_ty, dict)
                or _thr_ty.get("thresholds_yaml_file_bytes") is None
                else str(_thr_ty.get("thresholds_yaml_file_bytes"))
            )
            _thr_rows = [
                {
                    "field": "configs/integrator/thresholds.yaml version (int)",
                    "value": _thr_ver,
                },
                {
                    "field": "configs/integrator/thresholds.yaml on-disk size (bytes)",
                    "value": _thr_bytes,
                },
                {
                    "field": "pipeline effective min_score_to_pass",
                    "value": str(_thr_payload.get("pipeline_effective_min_score_to_pass")),
                },
                {
                    "field": "streamlit preview effective min_score_to_pass",
                    "value": str(_thr_payload.get("streamlit_preview_effective_min_score_to_pass")),
                },
                {
                    "field": "would_emit integrator gate event",
                    "value": str(
                        _thr_payload.get("gate_event_emission", {}).get(
                            "would_emit_integrator_gate_event",
                        ),
                    ),
                },
                {
                    "field": "workflow integrator_gate project_tags list length",
                    "value": "—"
                    if _thr_payload.get("workflow_integrator_gate", {}).get(
                        "project_tags_list_length",
                    )
                    is None
                    else str(
                        _thr_payload.get("workflow_integrator_gate", {}).get(
                            "project_tags_list_length",
                        ),
                    ),
                },
            ]
            st.dataframe(_thr_rows, use_container_width=True, hide_index=True)
            _thr_expl_rows = integrator_threshold_explainer_table_rows(_thr_payload)
            if _thr_expl_rows:
                _thr_expl_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                _thr_expl_slug = integrator_threshold_export_filename_slug()
                _thr_expl_json = integrator_threshold_explainer_export_json(_thr_payload)
                _thr_expl_csv = integrator_threshold_explainer_table_rows_csv(_thr_expl_rows)
                _thr_expl_dl_json_col, _thr_expl_dl_csv_col = st.columns(2)
                with _thr_expl_dl_json_col:
                    st.download_button(
                        label="Download integrator threshold explainer JSON",
                        data=_thr_expl_json.encode("utf-8"),
                        file_name=f"hermes_{_thr_expl_slug}_explainer_{_thr_expl_ts}.json",
                        mime="application/json",
                        key="hermes_dl_integrator_threshold_explainer_json",
                    )
                with _thr_expl_dl_csv_col:
                    if _thr_expl_csv:
                        st.download_button(
                            label="Download integrator threshold explainer CSV",
                            data=_thr_expl_csv.encode("utf-8"),
                            file_name=f"hermes_{_thr_expl_slug}_explainer_{_thr_expl_ts}.csv",
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_integrator_threshold_explainer_csv",
                        )
            with st.expander("Raw threshold explainer JSON", expanded=False):
                st.json(_thr_payload)
        st.text_input(
            "Bundle id (catalog ``bundles[].id``)",
            value="auth-rbac-starter",
            key="hermes_integrator_bundle_id",
        )
        st.text_area(
            "Synthetic ``tags`` JSON array (optional; overrides workflow ``project_tags`` when set)",
            value="[]",
            height=68,
            key="hermes_integrator_tags_json",
        )
        if st.button("Run integrator preview", key="hermes_integrator_preview_btn"):
            try:
                st.session_state[rl._LAST_INTEGRATOR_PREVIEW] = integrator_preview_payload(
                    _iroot,
                    workflow_profile=_wf_pick,
                    pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                    bundle_id=str(st.session_state.get("hermes_integrator_bundle_id", "")),
                    synthetic_tags_json=str(
                        st.session_state.get("hermes_integrator_tags_json", "[]"),
                    ),
                )
            except (OSError, ValueError) as _ix_exc:
                st.session_state.pop(rl._LAST_INTEGRATOR_PREVIEW, None)
                st.error(f"Preview failed: {_ix_exc}")
        _ip = st.session_state.get(rl._LAST_INTEGRATOR_PREVIEW)
        if isinstance(_ip, dict):
            _rows = [
                {"field": "workflow_profile", "value": str(_ip.get("workflow_profile"))},
                {
                    "field": "disk integrator_gate.enabled",
                    "value": str(_ip.get("disk_integrator_gate_enabled")),
                },
                {
                    "field": "thresholds.yaml enabled (catalog)",
                    "value": str(_ip.get("catalog_thresholds_enabled")),
                },
                {
                    "field": "pasted enabled (preview only)",
                    "value": str(_ip.get("pasted_enabled_preview")),
                },
                {
                    "field": "effective min_score_to_pass",
                    "value": str(_ip.get("effective_min_score_to_pass")),
                },
                {"field": "bundle_id", "value": str(_ip.get("bundle_id"))},
                {"field": "score_fit", "value": str(_ip.get("score_fit"))},
                {"field": "passes_gate", "value": str(_ip.get("passes_gate"))},
            ]
            _iperr = _ip.get("validation_errors")
            if isinstance(_iperr, list) and _iperr:
                for _e in _iperr:
                    st.warning(str(_e))
            st.dataframe(_rows, use_container_width=True, hide_index=True)
            with st.expander("Raw integrator preview JSON", expanded=False):
                st.json(_ip)
        _integrator_write_ok = workflow_yaml_write_enabled()
        st.caption(
            "Workflow YAML disk writes (**fo132** ``integrator_gate``, "
            "**fo140** ``agent_evaluator``, **§14 #13** full-profile merge): "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}`` is "
            f"{'**enabled**' if _integrator_write_ok else '**disabled** — no disk writes'}."
        )
        st.text_input(
            "Confirm profile stem for disk apply (type exactly the selected workflow profile)",
            key="hermes_integrator_confirm_profile",
        )
        with st.expander("Apply integrator_gate to disk (fo132)", expanded=False):
            st.caption(
                "Merges the pasted ``integrator_gate`` block into the **selected** workflow profile "
                "via ``atomic_write_yaml`` (other YAML keys preserved). Requires "
                f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on) in the Streamlit process env."
            )
            if st.button("Dry-run merge (no write)", key="hermes_integrator_dry_run_btn"):
                if not _wf_pick:
                    st.error("Select a workflow profile first.")
                else:
                    _mrg, _b4, _af, _merr = prepare_integrator_gate_apply(
                        _iroot,
                        profile_stem=str(_wf_pick),
                        pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                    )
                    st.session_state[rl.rl._LAST_INTEGRATOR_MERGE_DRY] = {
                        "profile": str(_wf_pick),
                        "before_gate": _b4,
                        "after_gate": _af,
                        "errors": _merr,
                        "merged_ok": _mrg is not None,
                    }
            _dry = st.session_state.get(rl._LAST_INTEGRATOR_MERGE_DRY)
            if isinstance(_dry, dict) and _dry.get("merged_ok"):
                st.caption("Dry-run ``integrator_gate`` (before → after)")
                _c1, _c2 = st.columns(2)
                with _c1:
                    st.json(_dry.get("before_gate"))
                with _c2:
                    st.json(_dry.get("after_gate"))
            elif isinstance(_dry, dict) and _dry.get("errors"):
                for _me in _dry["errors"]:
                    st.warning(str(_me))
            _confirm = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
            _can_apply = bool(
                _integrator_write_ok and _wf_pick and _confirm and _confirm == str(_wf_pick).strip(),
            )
            if st.button(
                "Apply merge to disk",
                disabled=not _can_apply,
                key="hermes_integrator_apply_disk_btn",
            ):
                _ok_ap, _merged_doc, _ap_errs = apply_integrator_gate_yaml(
                    _iroot,
                    profile_stem=str(_wf_pick),
                    pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                    confirm_profile_stem=_confirm,
                )
                if _ok_ap:
                    st.success("Wrote workflow YAML.")
                    st.session_state.pop(rl._LAST_INTEGRATOR_MERGE_DRY, None)
                else:
                    for _ap_e in _ap_errs:
                        st.error(str(_ap_e))
        with st.expander("Apply agent_evaluator to disk (fo140)", expanded=False):
            st.caption(
                "Merges the pasted ``agent_evaluator`` block into the **selected** workflow profile "
                "via ``atomic_write_yaml`` (other YAML keys preserved). Accepts a full workflow root "
                "with ``agent_evaluator:`` or a flat ``enabled`` / ``persona_id`` map. Requires "
                f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on) in the Streamlit process env. "
                "Uses the **same** profile-stem confirmation field as **fo132** above."
            )
            st.text_area(
                "Optional pasted ``agent_evaluator`` YAML (full workflow with key, or flat mapping)",
                height=120,
                placeholder="agent_evaluator:\n  enabled: true\n  persona_id: default\n",
                key="hermes_integrator_paste_agent_evaluator_yaml",
            )
            if st.button("Dry-run merge (no write)", key="hermes_integrator_ae_dry_run_btn"):
                if not _wf_pick:
                    st.error("Select a workflow profile first.")
                else:
                    _mrg_ae, _b4_ae, _af_ae, _merr_ae = prepare_agent_evaluator_apply(
                        _iroot,
                        profile_stem=str(_wf_pick),
                        pasted_yaml=str(
                            st.session_state.get("hermes_integrator_paste_agent_evaluator_yaml", ""),
                        ),
                    )
                    st.session_state[rl.rl._LAST_AGENT_EVALUATOR_MERGE_DRY] = {
                        "profile": str(_wf_pick),
                        "before_ae": _b4_ae,
                        "after_ae": _af_ae,
                        "errors": _merr_ae,
                        "merged_ok": _mrg_ae is not None,
                    }
            _dry_ae = st.session_state.get(rl._LAST_AGENT_EVALUATOR_MERGE_DRY)
            if isinstance(_dry_ae, dict) and _dry_ae.get("merged_ok"):
                st.caption("Dry-run ``agent_evaluator`` (before → after)")
                _ac1, _ac2 = st.columns(2)
                with _ac1:
                    st.json(_dry_ae.get("before_ae"))
                with _ac2:
                    st.json(_dry_ae.get("after_ae"))
            elif isinstance(_dry_ae, dict) and _dry_ae.get("errors"):
                for _me_ae in _dry_ae["errors"]:
                    st.warning(str(_me_ae))
            _confirm_ae = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
            _can_apply_ae = bool(
                _integrator_write_ok
                and _wf_pick
                and _confirm_ae
                and _confirm_ae == str(_wf_pick).strip(),
            )
            if st.button(
                "Apply agent_evaluator merge to disk",
                disabled=not _can_apply_ae,
                key="hermes_integrator_ae_apply_disk_btn",
            ):
                _ok_ae, _merged_ae, _ap_errs_ae = apply_agent_evaluator_yaml(
                    _iroot,
                    profile_stem=str(_wf_pick),
                    pasted_yaml=str(
                        st.session_state.get("hermes_integrator_paste_agent_evaluator_yaml", ""),
                    ),
                    confirm_profile_stem=_confirm_ae,
                )
                if _ok_ae:
                    st.success("Wrote workflow YAML.")
                    st.session_state.pop(rl._LAST_AGENT_EVALUATOR_MERGE_DRY, None)
                else:
                    for _ap_e_ae in _ap_errs_ae:
                        st.error(str(_ap_e_ae))
        with st.expander("Apply full workflow profile to disk (§14 #13)", expanded=False):
            st.caption(
                "Paste a **full** workflow root (same allowed top-level keys as shipped "
                "``configs/workflows/*.yaml`` profiles). Validates keys + ``integrator_gate`` / "
                "``agent_evaluator`` blocks; **shallow-merges** each pasted top-level key over the "
                "on-disk file (keys you omit from the paste are unchanged). Requires "
                f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on). Uses the **same** "
                "profile-stem confirmation field as **fo132** / **fo140** above."
            )
            st.text_area(
                "Pasted full workflow YAML",
                height=260,
                placeholder="version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n",
                key="hermes_full_workflow_paste_yaml",
            )
            if st.button("Dry-run full merge (no write)", key="hermes_full_workflow_dry_run_btn"):
                if not _wf_pick:
                    st.error("Select a workflow profile first.")
                else:
                    _mrg_fw, _b4_fw, _merr_fw = prepare_full_workflow_apply(
                        _iroot,
                        profile_stem=str(_wf_pick),
                        pasted_yaml=str(
                            st.session_state.get("hermes_full_workflow_paste_yaml", ""),
                        ),
                    )
                    st.session_state[rl.rl._LAST_FULL_WORKFLOW_MERGE_DRY] = {
                        "profile": str(_wf_pick),
                        "before_disk": _b4_fw,
                        "merged": _mrg_fw,
                        "errors": _merr_fw,
                        "merged_ok": _mrg_fw is not None,
                    }
            _dry_fw = st.session_state.get(rl._LAST_FULL_WORKFLOW_MERGE_DRY)
            if isinstance(_dry_fw, dict) and _dry_fw.get("merged_ok"):
                st.caption("Dry-run full profile (on-disk before vs merged preview)")
                _b4_d = _dry_fw.get("before_disk")
                _mrg_d = _dry_fw.get("merged")
                _paste_live, _ = parse_full_workflow_yaml_paste(
                    str(st.session_state.get("hermes_full_workflow_paste_yaml", "")),
                )
                _diff_fw = (
                    full_workflow_merge_diff(
                        _b4_d,
                        _mrg_d,
                        pasted_root=_paste_live if isinstance(_paste_live, dict) else None,
                    )
                    if isinstance(_b4_d, dict) and isinstance(_mrg_d, dict)
                    else None
                )
                with st.expander("Top-level merge diff summary", expanded=False):
                    if isinstance(_diff_fw, dict) and _diff_fw.get("error"):
                        st.warning(str(_diff_fw["error"]))
                    elif isinstance(_diff_fw, dict):
                        st.dataframe(
                            [
                                {
                                    "bucket": "added_top_level",
                                    "keys": ", ".join(_diff_fw.get("added_top_level_keys", []))
                                    or "—",
                                },
                                {
                                    "bucket": "removed_top_level",
                                    "keys": ", ".join(_diff_fw.get("removed_top_level_keys", []))
                                    or "—",
                                },
                                {
                                    "bucket": "changed_top_level",
                                    "keys": ", ".join(_diff_fw.get("changed_top_level_keys", []))
                                    or "—",
                                },
                                {
                                    "bucket": "unchanged_top_level",
                                    "keys": ", ".join(_diff_fw.get("unchanged_top_level_keys", []))
                                    or "—",
                                },
                                {
                                    "bucket": "disk_only_top_level",
                                    "keys": ", ".join(_diff_fw.get("disk_only_top_level_keys", []))
                                    or "—",
                                },
                                {
                                    "bucket": "paste_only_top_level",
                                    "keys": ", ".join(_diff_fw.get("paste_only_top_level_keys", []))
                                    or "—",
                                },
                                {
                                    "bucket": "pasted_top_level",
                                    "keys": ", ".join(_diff_fw.get("pasted_top_level_keys", []))
                                    or "—",
                                },
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )
                        _overview_fw = full_workflow_merge_overview_caption(_diff_fw)
                        if _overview_fw:
                            st.caption(_overview_fw)
                        _churn_n_fw = full_workflow_merge_top_level_churn_count_caption(_diff_fw)
                        if _churn_n_fw:
                            st.caption(_churn_n_fw)
                        _fw_fp = full_workflow_merge_diff_audit_fingerprint_caption(_diff_fw)
                        if _fw_fp:
                            st.caption(_fw_fp)
                        _unchurn_uc = full_workflow_merge_unchanged_with_churn_caption(_diff_fw)
                        if _unchurn_uc:
                            st.caption(_unchurn_uc)
                        _unchanged_fw = full_workflow_merge_unchanged_top_level_caption(
                            _diff_fw,
                        )
                        if _unchanged_fw:
                            st.caption(_unchanged_fw)
                        _changed_fw = full_workflow_merge_changed_top_level_caption(
                            _diff_fw,
                        )
                        if _changed_fw:
                            st.caption(_changed_fw)
                        _added_fw = full_workflow_merge_added_top_level_caption(
                            _diff_fw,
                        )
                        if _added_fw:
                            st.caption(_added_fw)
                        _removed_fw = full_workflow_merge_removed_top_level_caption(
                            _diff_fw,
                        )
                        if _removed_fw:
                            st.caption(_removed_fw)
                        _disk_only_fw = full_workflow_merge_disk_only_top_level_caption(
                            _diff_fw,
                        )
                        if _disk_only_fw:
                            st.caption(_disk_only_fw)
                        _paste_only_fw = full_workflow_merge_paste_only_top_level_caption(
                            _diff_fw,
                        )
                        if _paste_only_fw:
                            st.caption(_paste_only_fw)
                        _pasted_top_fw = full_workflow_merge_pasted_top_level_caption(_diff_fw)
                        if _pasted_top_fw:
                            st.caption(_pasted_top_fw)
                        _att_fw = full_workflow_merge_attention_rows(_diff_fw)
                        if _att_fw:
                            _att_fw_metrics = full_workflow_merge_attention_operator_metrics(_diff_fw)
                            _att_fw_metrics_cap = (
                                full_workflow_merge_attention_operator_metrics_caption(
                                    _att_fw_metrics,
                                )
                            )
                            if _att_fw_metrics_cap:
                                st.caption(_att_fw_metrics_cap)
                            _att_fw_metric_rows = (
                                full_workflow_merge_attention_operator_metrics_table_rows(
                                    _att_fw_metrics,
                                )
                            )
                            if _att_fw_metric_rows:
                                st.dataframe(
                                    _att_fw_metric_rows,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            _att_fw_metrics_ts = datetime.now(timezone.utc).strftime(
                                "%Y%m%dT%H%M%SZ",
                            )
                            _att_fw_metrics_slug = (
                                full_workflow_merge_attention_operator_metrics_export_filename_slug()
                            )
                            _att_fw_metrics_json = (
                                full_workflow_merge_attention_operator_metrics_export_json(
                                    _att_fw_metrics,
                                )
                            )
                            _att_fw_metrics_csv = (
                                full_workflow_merge_attention_operator_metrics_table_rows_csv(
                                    _att_fw_metric_rows,
                                )
                            )
                            _att_fw_m_dl_json_col, _att_fw_m_dl_csv_col = st.columns(2)
                            with _att_fw_m_dl_json_col:
                                st.download_button(
                                    label="Download merge attention operator metrics JSON",
                                    data=_att_fw_metrics_json.encode("utf-8"),
                                    file_name=(
                                        f"hermes_{_att_fw_metrics_slug}_{_att_fw_metrics_ts}.json"
                                    ),
                                    mime="application/json",
                                    key="hermes_dl_full_workflow_merge_attention_metrics_json",
                                )
                            with _att_fw_m_dl_csv_col:
                                if _att_fw_metrics_csv:
                                    st.download_button(
                                        label="Download merge attention operator metrics CSV",
                                        data=_att_fw_metrics_csv.encode("utf-8"),
                                        file_name=(
                                            f"hermes_{_att_fw_metrics_slug}_"
                                            f"{_att_fw_metrics_ts}.csv"
                                        ),
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_full_workflow_merge_attention_metrics_csv",
                                    )
                            st.caption("Full-profile merge attention (read-only hints; §14 #13).")
                            st.dataframe(_att_fw, use_container_width=True, hide_index=True)
                            _att_fw_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                            _att_fw_slug = full_workflow_merge_attention_export_filename_slug()
                            _att_fw_json = full_workflow_merge_attention_export_json(_att_fw)
                            _att_fw_csv = full_workflow_merge_attention_table_rows_csv(_att_fw)
                            _att_fw_dl_json_col, _att_fw_dl_csv_col = st.columns(2)
                            with _att_fw_dl_json_col:
                                st.download_button(
                                    label="Download full-workflow merge attention JSON",
                                    data=_att_fw_json.encode("utf-8"),
                                    file_name=f"hermes_{_att_fw_slug}_{_att_fw_ts}.json",
                                    mime="application/json",
                                    key="hermes_dl_full_workflow_merge_attention_json",
                                )
                            with _att_fw_dl_csv_col:
                                if _att_fw_csv:
                                    st.download_button(
                                        label="Download full-workflow merge attention CSV",
                                        data=_att_fw_csv.encode("utf-8"),
                                        file_name=f"hermes_{_att_fw_slug}_{_att_fw_ts}.csv",
                                        mime="text/csv; charset=utf-8",
                                        key="hermes_dl_full_workflow_merge_attention_csv",
                                    )
                        _sub_fw = _diff_fw.get("subtree_field_diffs")
                        if isinstance(_sub_fw, dict) and _sub_fw:
                            st.caption(
                                "Shallow field churn (``integrator_gate`` / ``agent_evaluator`` only; "
                                "see raw JSON for before/after values)."
                            )
                            _sub_overview_fw = full_workflow_merge_subtree_overview_caption(
                                _diff_fw,
                            )
                            if _sub_overview_fw:
                                st.caption(_sub_overview_fw)
                            _sub_changed_fields_fw = (
                                full_workflow_merge_subtree_changed_fields_caption(_diff_fw)
                            )
                            if _sub_changed_fields_fw:
                                st.caption(_sub_changed_fields_fw)
                            _sub_added_fields_fw = full_workflow_merge_subtree_added_fields_caption(
                                _diff_fw,
                            )
                            if _sub_added_fields_fw:
                                st.caption(_sub_added_fields_fw)
                            _sub_removed_fields_fw = (
                                full_workflow_merge_subtree_removed_fields_caption(_diff_fw)
                            )
                            if _sub_removed_fields_fw:
                                st.caption(_sub_removed_fields_fw)
                            _rows_sub: list[dict[str, str]] = []
                            for _name, _blk in _sub_fw.items():
                                if not isinstance(_blk, dict):
                                    continue
                                _rows_sub.append(
                                    {
                                        "subtree": str(_name),
                                        "added": ", ".join(_blk.get("added_keys", [])) or "—",
                                        "removed": ", ".join(_blk.get("removed_keys", [])) or "—",
                                        "changed": ", ".join(_blk.get("changed_keys", [])) or "—",
                                        "unchanged": ", ".join(_blk.get("unchanged_keys", [])) or "—",
                                    },
                                )
                            if _rows_sub:
                                st.dataframe(_rows_sub, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No diff payload (unexpected).")
                if isinstance(_diff_fw, dict) and not _diff_fw.get("error"):
                    _diff_fw_metrics = full_workflow_merge_diff_operator_metrics(_diff_fw)
                    _diff_fw_metrics_cap = full_workflow_merge_diff_operator_metrics_caption(
                        _diff_fw_metrics,
                    )
                    if _diff_fw_metrics_cap:
                        st.caption(_diff_fw_metrics_cap)
                    _diff_fw_metric_rows = full_workflow_merge_diff_operator_metrics_table_rows(
                        _diff_fw_metrics,
                    )
                    if _diff_fw_metric_rows:
                        st.dataframe(
                            _diff_fw_metric_rows,
                            use_container_width=True,
                            hide_index=True,
                        )
                    _diff_fw_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                    _diff_fw_metrics_slug = (
                        full_workflow_merge_diff_operator_metrics_export_filename_slug()
                    )
                    _diff_fw_metrics_json = full_workflow_merge_diff_operator_metrics_export_json(
                        _diff_fw_metrics,
                    )
                    _diff_fw_metrics_csv = (
                        full_workflow_merge_diff_operator_metrics_table_rows_csv(
                            _diff_fw_metric_rows,
                        )
                    )
                    _diff_fw_m_dl_json_col, _diff_fw_m_dl_csv_col = st.columns(2)
                    with _diff_fw_m_dl_json_col:
                        st.download_button(
                            label="Download merge diff operator metrics JSON",
                            data=_diff_fw_metrics_json.encode("utf-8"),
                            file_name=(
                                f"hermes_{_diff_fw_metrics_slug}_{_diff_fw_ts}.json"
                            ),
                            mime="application/json",
                            key="hermes_dl_full_workflow_merge_diff_metrics_json",
                        )
                    with _diff_fw_m_dl_csv_col:
                        if _diff_fw_metrics_csv:
                            st.download_button(
                                label="Download merge diff operator metrics CSV",
                                data=_diff_fw_metrics_csv.encode("utf-8"),
                                file_name=(
                                    f"hermes_{_diff_fw_metrics_slug}_{_diff_fw_ts}.csv"
                                ),
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_full_workflow_merge_diff_metrics_csv",
                            )
                    _diff_fw_rows = full_workflow_merge_diff_table_rows(_diff_fw)
                    if _diff_fw_rows:
                        _diff_fw_slug = full_workflow_merge_diff_export_filename_slug()
                        _diff_fw_json = full_workflow_merge_diff_export_json(_diff_fw)
                        _diff_fw_csv = full_workflow_merge_diff_table_rows_csv(_diff_fw_rows)
                        _diff_fw_dl_json_col, _diff_fw_dl_csv_col = st.columns(2)
                        with _diff_fw_dl_json_col:
                            st.download_button(
                                label="Download full-workflow merge diff JSON",
                                data=_diff_fw_json.encode("utf-8"),
                                file_name=(
                                    f"hermes_{_diff_fw_slug}_"
                                    f"{_diff_fw_ts}.json"
                                ),
                                mime="application/json",
                                key="hermes_dl_full_workflow_merge_diff_json",
                            )
                        with _diff_fw_dl_csv_col:
                            if _diff_fw_csv:
                                st.download_button(
                                    label="Download full-workflow merge diff CSV",
                                    data=_diff_fw_csv.encode("utf-8"),
                                    file_name=(
                                        f"hermes_{_diff_fw_slug}_"
                                        f"{_diff_fw_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_full_workflow_merge_diff_csv",
                                )
                with st.expander("Raw full-workflow merge diff JSON", expanded=False):
                    st.json(_diff_fw if isinstance(_diff_fw, dict) else {})
                _fc1, _fc2 = st.columns(2)
                with _fc1:
                    st.json(_dry_fw.get("before_disk"))
                with _fc2:
                    st.json(_dry_fw.get("merged"))
                with st.expander("Raw merged full-workflow JSON", expanded=False):
                    st.json(_dry_fw.get("merged"))
            elif isinstance(_dry_fw, dict) and _dry_fw.get("errors"):
                for _me_fw in _dry_fw["errors"]:
                    st.warning(str(_me_fw))
            _confirm_fw = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
            _can_apply_fw = bool(
                _integrator_write_ok
                and _wf_pick
                and _confirm_fw
                and _confirm_fw == str(_wf_pick).strip(),
            )
            if st.button(
                "Apply full workflow merge to disk",
                disabled=not _can_apply_fw,
                key="hermes_full_workflow_apply_disk_btn",
            ):
                _ok_fw, _merged_fw, _ap_errs_fw = apply_full_workflow_yaml(
                    _iroot,
                    profile_stem=str(_wf_pick),
                    pasted_yaml=str(
                        st.session_state.get("hermes_full_workflow_paste_yaml", ""),
                    ),
                    confirm_profile_stem=_confirm_fw,
                )
                if _ok_fw:
                    st.success("Wrote workflow YAML.")
                    st.session_state.pop(rl._LAST_FULL_WORKFLOW_MERGE_DRY, None)
                else:
                    for _ap_e_fw in _ap_errs_fw:
                        st.error(str(_ap_e_fw))
