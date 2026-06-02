from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.components.explainer_panel import render_explainer_export_downloads
from nimbusware_console.components.workflow_explainer_helpers import (
    render_workflow_explainer_metrics_panel,
)
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_agent_evaluator_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Agent evaluator (workflow + env)", expanded=False):
        st.caption(
            "Read-only: ``agent_evaluator`` from the **same** profile stem vs "
            "``HERMES_AGENT_EVALUATOR`` — **yaml_parsed_*** is frozen YAML; "
            "**would_emit_stage_started** matches ``_maybe_emit_agent_evaluator_stage`` "
            "before create-run persona checks (kill-switch ``0``/``false``/``no``; "
            "``1``/``true``/``yes`` forces on). **persona_id** is always from the parsed "
            "workflow block when a stage would emit."
        )
        _ae_expl = agent_evaluator_workflow_explainer_payload(
            repo_root,
            workflow_profile=workflow_profile,
        )
        _ae_expl_metrics, _ae_expl_metric_rows = render_workflow_explainer_metrics_panel(
            _ae_expl,
            metrics_fn=agent_evaluator_workflow_explainer_operator_metrics,
            metrics_table_rows_fn=agent_evaluator_workflow_explainer_operator_metrics_table_rows,
            metrics_caption_fn=agent_evaluator_workflow_explainer_operator_metrics_caption,
            filename_slug=agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug(),
            json_label="Download agent evaluator operator metrics JSON",
            csv_label="Download agent evaluator operator metrics CSV",
            json_download_key="hermes_dl_agent_evaluator_explainer_metrics_json",
            csv_download_key="hermes_dl_agent_evaluator_explainer_metrics_csv",
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
            render_explainer_export_downloads(
                json_text=agent_evaluator_explainer_export_json(_ae_expl),
                csv_text=agent_evaluator_explainer_table_rows_csv(_ae_expl_rows),
                filename_slug=agent_evaluator_export_filename_slug(),
                json_label="Download agent evaluator explainer JSON",
                csv_label="Download agent evaluator explainer CSV",
                json_download_key="hermes_dl_agent_evaluator_explainer_json",
                csv_download_key="hermes_dl_agent_evaluator_explainer_csv",
            )
        with st.expander("Raw agent evaluator explainer JSON", expanded=False):
            st.json(_ae_expl)
