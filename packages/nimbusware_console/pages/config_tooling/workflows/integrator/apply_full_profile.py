from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_apply_full_profile_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Apply full workflow profile to disk", expanded=False):
        st.caption(
            "Paste a **full** workflow root (same allowed top-level keys as shipped "
            "``configs/workflows/*.yaml`` profiles). Validates keys + ``integrator_gate`` / "
            "``agent_evaluator`` blocks; **shallow-merges** each pasted top-level key over the "
            "on-disk file (keys you omit from the paste are unchanged). Requires "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on). Uses the **same** "
            "profile-stem confirmation field as the integrator gate and agent evaluator apply panels above."
        )
        st.text_area(
            "Pasted full workflow YAML",
            height=260,
            placeholder="version: 1\nintegrator_gate:\n  enabled: true\n  min_score_to_pass: 0.5\n",
            key="hermes_full_workflow_paste_yaml",
        )
        if st.button("Dry-run full merge (no write)", key="hermes_full_workflow_dry_run_btn"):
            if not workflow_profile:
                st.error("Select a workflow profile first.")
            else:
                _mrg_fw, _b4_fw, _merr_fw = prepare_full_workflow_apply(
                    repo_root,
                    profile_stem=str(workflow_profile),
                    pasted_yaml=str(
                        st.session_state.get("hermes_full_workflow_paste_yaml", ""),
                    ),
                )
                st.session_state[rl.rl._LAST_FULL_WORKFLOW_MERGE_DRY] = {
                    "profile": str(workflow_profile),
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
                                "keys": ", ".join(_diff_fw.get("added_top_level_keys", [])) or "—",
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
                                "keys": ", ".join(_diff_fw.get("pasted_top_level_keys", [])) or "—",
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
                                        f"hermes_{_att_fw_metrics_slug}_{_att_fw_metrics_ts}.csv"
                                    ),
                                    mime="text/csv; charset=utf-8",
                                    key="hermes_dl_full_workflow_merge_attention_metrics_csv",
                                )
                        st.caption("Full-profile merge attention (read-only hints).")
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
                        _sub_changed_fields_fw = full_workflow_merge_subtree_changed_fields_caption(
                            _diff_fw
                        )
                        if _sub_changed_fields_fw:
                            st.caption(_sub_changed_fields_fw)
                        _sub_added_fields_fw = full_workflow_merge_subtree_added_fields_caption(
                            _diff_fw,
                        )
                        if _sub_added_fields_fw:
                            st.caption(_sub_added_fields_fw)
                        _sub_removed_fields_fw = full_workflow_merge_subtree_removed_fields_caption(
                            _diff_fw
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
                _diff_fw_metrics_csv = full_workflow_merge_diff_operator_metrics_table_rows_csv(
                    _diff_fw_metric_rows,
                )
                _diff_fw_m_dl_json_col, _diff_fw_m_dl_csv_col = st.columns(2)
                with _diff_fw_m_dl_json_col:
                    st.download_button(
                        label="Download merge diff operator metrics JSON",
                        data=_diff_fw_metrics_json.encode("utf-8"),
                        file_name=(f"hermes_{_diff_fw_metrics_slug}_{_diff_fw_ts}.json"),
                        mime="application/json",
                        key="hermes_dl_full_workflow_merge_diff_metrics_json",
                    )
                with _diff_fw_m_dl_csv_col:
                    if _diff_fw_metrics_csv:
                        st.download_button(
                            label="Download merge diff operator metrics CSV",
                            data=_diff_fw_metrics_csv.encode("utf-8"),
                            file_name=(f"hermes_{_diff_fw_metrics_slug}_{_diff_fw_ts}.csv"),
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
                            file_name=(f"hermes_{_diff_fw_slug}_{_diff_fw_ts}.json"),
                            mime="application/json",
                            key="hermes_dl_full_workflow_merge_diff_json",
                        )
                    with _diff_fw_dl_csv_col:
                        if _diff_fw_csv:
                            st.download_button(
                                label="Download full-workflow merge diff CSV",
                                data=_diff_fw_csv.encode("utf-8"),
                                file_name=(f"hermes_{_diff_fw_slug}_{_diff_fw_ts}.csv"),
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
            and workflow_profile
            and _confirm_fw
            and _confirm_fw == str(workflow_profile).strip(),
        )
        if st.button(
            "Apply full workflow merge to disk",
            disabled=not _can_apply_fw,
            key="hermes_full_workflow_apply_disk_btn",
        ):
            _ok_fw, _merged_fw, _ap_errs_fw = apply_full_workflow_yaml(
                repo_root,
                profile_stem=str(workflow_profile),
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
