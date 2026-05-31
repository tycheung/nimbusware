from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    Path,
    datetime,
    os,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_a import (
    agent_evaluator_auto_actions_caption,
    agent_evaluator_auto_actions_table_rows,
    agent_evaluator_coverage_gate_caption,
    agent_evaluator_env_gate_caption,
    agent_evaluator_evaluation_branch_caption,
    agent_evaluator_evaluation_caption,
    agent_evaluator_explainer_table_rows,
    agent_evaluator_from_timeline,
    agent_evaluator_llm_evaluation_enabled_caption,
    agent_evaluator_operator_metrics,
    agent_evaluator_operator_metrics_caption,
    agent_evaluator_operator_metrics_export_filename_slug,
    agent_evaluator_operator_metrics_export_json,
    agent_evaluator_operator_metrics_table_rows,
    agent_evaluator_operator_metrics_table_rows_csv,
    agent_evaluator_persona_id_caption,
    agent_evaluator_session_caption,
    agent_evaluator_summary_rows,
    agent_evaluator_timeline_export_filename_slug,
    agent_evaluator_timeline_export_json,
    agent_evaluator_timeline_table_rows_csv,
    agent_evaluator_workflow_explainer_operator_metrics,
    agent_evaluator_workflow_explainer_operator_metrics_caption,
    agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug,
    agent_evaluator_workflow_explainer_operator_metrics_export_json,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv,
    agent_evaluator_workflow_explainer_payload,
    agent_evaluator_workflow_yaml_version_caption,
    agent_evaluator_would_emit_caption,
    agent_evaluator_yaml_key_present_caption,
    agent_evaluator_yaml_parsed_enabled_caption,
    persona_assignment_caption,
    persona_assignment_from_timeline,
    persona_assignment_summary_rows,
    persona_assignment_timeline_export_json,
    persona_assignment_timeline_table_rows_csv,
)
from nimbusware_console.pages.run_detail._imports_display_b import (
    self_refinement_auto_promote_caption,
    self_refinement_description_length_caption,
    self_refinement_evaluation_caption,
    self_refinement_explainer_table_rows,
    self_refinement_from_timeline,
    self_refinement_iteration_caption,
    self_refinement_latest_export_filename_slug,
    self_refinement_latest_export_json,
    self_refinement_latest_summary_rows_csv,
    self_refinement_llm_critique_stage_caption,
    self_refinement_marker_avg_interval_caption,
    self_refinement_marker_first_last_caption,
    self_refinement_marker_window_caption,
    self_refinement_markers_per_minute_caption,
    self_refinement_merged_description_preview_caption,
    self_refinement_merged_version_caption,
    self_refinement_phase_d_signal_caption,
    self_refinement_policy_attempt_caption,
    self_refinement_policy_yaml_disk_version_caption,
    self_refinement_policy_yaml_file_bytes_caption,
    self_refinement_prior_gate_verdict_caption,
    self_refinement_session_caption,
    self_refinement_stage_name_caption,
    self_refinement_summary_rows,
    self_refinement_timeline_metrics_table_rows,
    self_refinement_timeline_operator_metrics,
    self_refinement_timeline_operator_metrics_export_filename_slug,
    self_refinement_timeline_operator_metrics_export_json,
    self_refinement_timeline_operator_metrics_table_rows_csv,
    self_refinement_timeline_policy_version_caption,
    self_refinement_ungated_loop_caption,
    self_refinement_ungated_loop_env_gate_caption,
    self_refinement_version_attempt_caption,
    self_refinement_workflow_explainer_operator_metrics,
    self_refinement_workflow_explainer_operator_metrics_caption,
    self_refinement_workflow_explainer_operator_metrics_export_filename_slug,
    self_refinement_workflow_explainer_operator_metrics_export_json,
    self_refinement_workflow_explainer_operator_metrics_table_rows,
    self_refinement_workflow_explainer_operator_metrics_table_rows_csv,
    self_refinement_workflow_explainer_payload,
    self_refinement_workflow_yaml_raw_type_caption,
    self_refinement_would_emit_after_env_caption,
    self_refinement_would_emit_marker_caption,
)
from nimbusware_console.pages.run_detail._imports_tail import _iroot


def _workflow_profile_pick(data: dict[str, Any]) -> str:
    wf = data.get("workflow_profile") if isinstance(data, dict) else None
    if isinstance(wf, str) and wf.strip():
        return wf.strip()
    return os.environ.get("HERMES_WORKFLOW_PROFILE", "nimbusware_production")


def _run_slug(run_id: str, *, max_len: int = 36) -> str:
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_id.strip())
    return (slug or "run")[:max_len]


def _workflow_profile_pick(data: dict[str, Any]) -> str:
    wf = data.get("workflow_profile") if isinstance(data, dict) else None
    if isinstance(wf, str) and wf.strip():
        return wf.strip()
    return os.environ.get("HERMES_WORKFLOW_PROFILE", "nimbusware_production")


def _run_slug(run_id: str, *, max_len: int = 36) -> str:
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_id.strip())
    return (slug or "run")[:max_len]


def _render_persona_assignment(run_id: str, data: dict) -> None:
    _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _slug = _run_slug(run_id.strip())

    _pa = persona_assignment_from_timeline(data)
    _pa_rows = persona_assignment_summary_rows(_pa)
    with st.expander("Persona assignment (from timeline)", expanded=False):
        if not _pa_rows:
            st.caption(
                "No persona_assignment on this timeline (create_run did not "
                "set business_area_persona_id / development_role_persona_id)."
            )
        else:
            st.caption(
                "Frozen composite persona from the first run.created "
                "(same top-level persona_assignment as GET …/timeline)."
            )
            _pa_cap = persona_assignment_caption(_pa)
            if _pa_cap:
                st.caption(_pa_cap)
            st.dataframe(_pa_rows, use_container_width=True)
            _pa_csv = persona_assignment_timeline_table_rows_csv(_pa_rows)
            _pa_json = persona_assignment_timeline_export_json(_pa)
            _pa_dl_col, _pa_dl_json_col = st.columns(2)
            with _pa_dl_col:
                st.download_button(
                    label="Download persona assignment CSV",
                    data=_pa_csv.encode("utf-8"),
                    file_name=f"hermes_persona_assignment_{_slug}_{_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_persona_assignment_csv",
                )
            with _pa_dl_json_col:
                st.download_button(
                    label="Download persona assignment JSON",
                    data=_pa_json.encode("utf-8"),
                    file_name=f"hermes_persona_assignment_{_slug}_{_ts}.json",
                    mime="application/json",
                    key="hermes_dl_persona_assignment_json",
                )
            with st.expander("Raw persona_assignment JSON", expanded=False):
                st.json(_pa)

