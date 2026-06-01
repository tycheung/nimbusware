from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.components.explainer_panel import render_explainer_export_downloads
from nimbusware_console.components.workflow_explainer_helpers import (
    render_workflow_explainer_metrics_panel,
)
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_escalation_suppress_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Escalation suppress (workflow YAML, fo137)", expanded=False):
        st.caption(
            "Read-only: ``escalation.suppress_automatic_escalation`` from the **same** profile "
            "stem — **suppress_automatic_escalation_effective** matches "
            "``parse_escalation_workflow_block`` (same boolean the pipeline uses in "
            "``_workflow_suppresses_automatic_escalation`` once the run profile resolves to "
            "this stem). Non-dict ``escalation:`` collapses to off. PLAN_GAP §14 #19."
        )
        _es_expl = escalation_suppress_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
        _es_expl_metrics, _es_expl_metric_rows = render_workflow_explainer_metrics_panel(
            _es_expl,
            metrics_fn=escalation_suppress_workflow_explainer_operator_metrics,
            metrics_table_rows_fn=escalation_suppress_workflow_explainer_operator_metrics_table_rows,
            metrics_caption_fn=escalation_suppress_workflow_explainer_operator_metrics_caption,
            filename_slug=escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug(),
            json_label="Download escalation suppress operator metrics JSON",
            csv_label="Download escalation suppress operator metrics CSV",
            json_download_key="hermes_dl_escalation_suppress_explainer_metrics_json",
            csv_download_key="hermes_dl_escalation_suppress_explainer_metrics_csv",
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
            render_explainer_export_downloads(
                json_text=escalation_suppress_explainer_export_json(_es_expl),
                csv_text=escalation_suppress_explainer_table_rows_csv(_es_expl_rows),
                filename_slug=escalation_suppress_export_filename_slug(),
                json_label="Download escalation suppress explainer JSON",
                csv_label="Download escalation suppress explainer CSV",
                json_download_key="hermes_dl_escalation_suppress_explainer_json",
                csv_download_key="hermes_dl_escalation_suppress_explainer_csv",
            )
        with st.expander("Raw escalation suppress explainer JSON", expanded=False):
            st.json(_es_expl)
