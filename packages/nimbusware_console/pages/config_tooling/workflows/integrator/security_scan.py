from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.components.explainer_panel import render_explainer_export_downloads
from nimbusware_console.components.workflow_explainer_helpers import (
    render_workflow_explainer_metrics_panel,
)
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_security_scan_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Security scan metadata on verify (workflow + env, fo136)", expanded=False):
        st.caption(
            "Read-only: ``security_scan_metadata_on_verify`` from the **same** workflow profile vs "
            "``HERMES_ATTACH_SECURITY_SCAN_METADATA`` — **yaml_parsed_bool** is frozen YAML only; "
            "**effective_enabled** matches ``security_scan_metadata_on_verify_enabled`` "
            "(truthy env forces on; ``0`` / ``false`` / ``no`` kill-switch). PLAN_GAP §14 #18."
        )
        _ssm_expl = security_scan_metadata_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
        _ssm_expl_metrics, _ssm_expl_metric_rows = render_workflow_explainer_metrics_panel(
            _ssm_expl,
            metrics_fn=security_scan_metadata_workflow_explainer_operator_metrics,
            metrics_table_rows_fn=security_scan_metadata_workflow_explainer_operator_metrics_table_rows,
            metrics_caption_fn=security_scan_metadata_workflow_explainer_operator_metrics_caption,
            filename_slug=security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug(),
            json_label="Download security scan metadata operator metrics JSON",
            csv_label="Download security scan metadata operator metrics CSV",
            json_download_key="hermes_dl_security_scan_metadata_explainer_metrics_json",
            csv_download_key="hermes_dl_security_scan_metadata_explainer_metrics_csv",
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
            render_explainer_export_downloads(
                json_text=security_scan_metadata_explainer_export_json(_ssm_expl),
                csv_text=security_scan_metadata_explainer_table_rows_csv(_ssm_expl_rows),
                filename_slug=security_scan_metadata_export_filename_slug(),
                json_label="Download security scan metadata explainer JSON",
                csv_label="Download security scan metadata explainer CSV",
                json_download_key="hermes_dl_security_scan_metadata_explainer_json",
                csv_download_key="hermes_dl_security_scan_metadata_explainer_csv",
            )
        with st.expander("Raw security scan metadata explainer JSON", expanded=False):
            st.json(_ssm_expl)
