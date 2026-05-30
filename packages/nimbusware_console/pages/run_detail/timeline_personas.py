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


def render_run_detail_timeline_personas(run_id: str, data: dict) -> None:
    _wf_pick = _workflow_profile_pick(data)
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
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

    _ae = agent_evaluator_from_timeline(data)
    _ae_rows = agent_evaluator_summary_rows(_ae)
    with st.expander("Agent evaluator (from timeline)", expanded=False):
        if not _ae_rows:
            st.caption(
                "No agent_evaluator summary on this timeline (no agent-evaluator "
                "stage.started yet, or evaluator disabled for this run)."
            )
        else:
            st.caption(
                "Latest agent-evaluator stage.started summary (same top-level "
                "agent_evaluator as GET …/timeline)."
            )
            for cap_fn in (
                agent_evaluator_session_caption,
                agent_evaluator_evaluation_caption,
                agent_evaluator_evaluation_branch_caption,
                agent_evaluator_coverage_gate_caption,
                agent_evaluator_auto_actions_caption,
            ):
                cap = cap_fn(_ae)
                if cap:
                    st.caption(cap)
            _ae_auto_rows = agent_evaluator_auto_actions_table_rows(_ae)
            if _ae_auto_rows:
                st.caption("Auto-create / auto-promote actions from timeline metadata")
                st.dataframe(_ae_auto_rows, use_container_width=True, hide_index=True)
            st.dataframe(_ae_rows, use_container_width=True)
            _ae_metrics = agent_evaluator_operator_metrics(_ae)
            _ae_metrics_cap = agent_evaluator_operator_metrics_caption(_ae_metrics)
            if _ae_metrics_cap:
                st.caption(_ae_metrics_cap)
            _ae_metric_rows = agent_evaluator_operator_metrics_table_rows(_ae_metrics)
            if _ae_metric_rows:
                st.dataframe(
                    _ae_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _ae_metrics_json = agent_evaluator_operator_metrics_export_json(_ae_metrics)
                _ae_metrics_csv = agent_evaluator_operator_metrics_table_rows_csv(
                    _ae_metric_rows,
                )
                _ae_metrics_slug = agent_evaluator_operator_metrics_export_filename_slug(
                    run_id.strip(),
                )
                _ae_metrics_dl_json_col, _ae_metrics_dl_csv_col = st.columns(2)
                with _ae_metrics_dl_json_col:
                    st.download_button(
                        label="Download agent evaluator operator metrics JSON",
                        data=_ae_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_agent_evaluator_operator_metrics_"
                            f"{_ae_metrics_slug}_{_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_agent_evaluator_operator_metrics_json",
                    )
                with _ae_metrics_dl_csv_col:
                    if _ae_metrics_csv:
                        st.download_button(
                            label="Download agent evaluator operator metrics CSV",
                            data=_ae_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_agent_evaluator_operator_metrics_"
                                f"{_ae_metrics_slug}_{_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_agent_evaluator_operator_metrics_csv",
                        )
            _ae_csv = agent_evaluator_timeline_table_rows_csv(_ae)
            _ae_json = agent_evaluator_timeline_export_json(_ae)
            _ae_tl_slug = agent_evaluator_timeline_export_filename_slug(run_id.strip())
            _ae_dl_col, _ae_dl_json_col = st.columns(2)
            with _ae_dl_col:
                st.download_button(
                    label="Download agent evaluator timeline CSV",
                    data=_ae_csv.encode("utf-8"),
                    file_name=f"hermes_agent_evaluator_timeline_{_ae_tl_slug}_{_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_agent_evaluator_timeline_csv",
                )
            with _ae_dl_json_col:
                st.download_button(
                    label="Download agent evaluator timeline JSON",
                    data=_ae_json.encode("utf-8"),
                    file_name=f"hermes_agent_evaluator_timeline_{_ae_tl_slug}_{_ts}.json",
                    mime="application/json",
                    key="hermes_dl_agent_evaluator_timeline_json",
                )
            _ae_expl = agent_evaluator_workflow_explainer_payload(_iroot, workflow_profile=_wf_pick)
            with st.expander("Agent evaluator workflow explainer (read-only)", expanded=False):
                for cap_fn in (
                    agent_evaluator_yaml_key_present_caption,
                    agent_evaluator_yaml_parsed_enabled_caption,
                    agent_evaluator_llm_evaluation_enabled_caption,
                    agent_evaluator_env_gate_caption,
                    agent_evaluator_would_emit_caption,
                    agent_evaluator_workflow_yaml_version_caption,
                    agent_evaluator_persona_id_caption,
                ):
                    cap = cap_fn(_ae_expl)
                    if cap:
                        st.caption(cap)
                _ae_expl_rows = agent_evaluator_explainer_table_rows(_ae_expl)
                if _ae_expl_rows:
                    st.dataframe(_ae_expl_rows, use_container_width=True, hide_index=True)
                _ae_expl_metrics = agent_evaluator_workflow_explainer_operator_metrics(_ae_expl)
                _ae_expl_metrics_cap = agent_evaluator_workflow_explainer_operator_metrics_caption(
                    _ae_expl_metrics,
                )
                if _ae_expl_metrics_cap:
                    st.caption(_ae_expl_metrics_cap)
                _ae_expl_metric_rows = (
                    agent_evaluator_workflow_explainer_operator_metrics_table_rows(
                        _ae_expl_metrics,
                    )
                )
                if _ae_expl_metric_rows:
                    st.dataframe(
                        _ae_expl_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _ae_expl_metrics_json = (
                        agent_evaluator_workflow_explainer_operator_metrics_export_json(
                            _ae_expl_metrics,
                        )
                    )
                    _ae_expl_metrics_csv = (
                        agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv(
                            _ae_expl_metric_rows,
                        )
                    )
                    _ae_expl_metrics_slug = (
                        agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug()
                    )
                    _ae_expl_dl_json_col, _ae_expl_dl_csv_col = st.columns(2)
                    with _ae_expl_dl_json_col:
                        st.download_button(
                            label="Download agent evaluator explainer metrics JSON",
                            data=_ae_expl_metrics_json.encode("utf-8"),
                            file_name=f"hermes_{_ae_expl_metrics_slug}_{_ts}.json",
                            mime="application/json",
                            key="hermes_dl_agent_evaluator_explainer_metrics_json",
                        )
                    with _ae_expl_dl_csv_col:
                        if _ae_expl_metrics_csv:
                            st.download_button(
                                label="Download agent evaluator explainer metrics CSV",
                                data=_ae_expl_metrics_csv.encode("utf-8"),
                                file_name=f"hermes_{_ae_expl_metrics_slug}_{_ts}.csv",
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_agent_evaluator_explainer_metrics_csv",
                            )
                with st.expander("Raw agent evaluator explainer JSON", expanded=False):
                    st.json(_ae_expl)
            with st.expander("Raw agent_evaluator JSON", expanded=False):
                st.json(_ae)

    _sr = self_refinement_from_timeline(data)
    _sr_rows = self_refinement_summary_rows(_sr)
    with st.expander("Self-refinement (from timeline)", expanded=False):
        if not _sr_rows:
            st.caption(
                "No self_refinement summary on this timeline (no "
                "self_refinement:policy stage.started yet, or self-refinement "
                "disabled for this run)."
            )
        else:
            st.caption(
                "Latest self-refinement policy marker summary (same top-level "
                "self_refinement as GET …/timeline)."
            )
            for cap_fn in (
                self_refinement_version_attempt_caption,
                self_refinement_policy_attempt_caption,
                self_refinement_stage_name_caption,
                self_refinement_evaluation_caption,
                self_refinement_iteration_caption,
                self_refinement_ungated_loop_caption,
                self_refinement_auto_promote_caption,
                self_refinement_prior_gate_verdict_caption,
                self_refinement_phase_d_signal_caption,
                self_refinement_llm_critique_stage_caption,
                self_refinement_session_caption,
                self_refinement_description_length_caption,
                self_refinement_marker_first_last_caption,
                self_refinement_marker_window_caption,
                self_refinement_markers_per_minute_caption,
                self_refinement_marker_avg_interval_caption,
            ):
                cap = cap_fn(_sr)
                if cap:
                    st.caption(cap)
            st.dataframe(_sr_rows, use_container_width=True)
            _sr_metrics = self_refinement_timeline_operator_metrics(_sr)
            _sr_metric_rows = self_refinement_timeline_metrics_table_rows(_sr_metrics)
            if _sr_metric_rows:
                st.caption("Operator drill-down on timeline self_refinement summary")
                st.dataframe(
                    _sr_metric_rows,
                    use_container_width=True,
                    hide_index=True,
                )
                _sr_metrics_json = self_refinement_timeline_operator_metrics_export_json(
                    _sr_metrics,
                )
                _sr_metrics_csv = self_refinement_timeline_operator_metrics_table_rows_csv(
                    _sr_metric_rows,
                )
                _sr_metrics_slug = self_refinement_timeline_operator_metrics_export_filename_slug(
                    run_id.strip(),
                )
                _sr_metrics_dl_json_col, _sr_metrics_dl_csv_col = st.columns(2)
                with _sr_metrics_dl_json_col:
                    st.download_button(
                        label="Download self-refinement operator metrics JSON",
                        data=_sr_metrics_json.encode("utf-8"),
                        file_name=(
                            "hermes_self_refinement_operator_metrics_"
                            f"{_sr_metrics_slug}_{_ts}.json"
                        ),
                        mime="application/json",
                        key="hermes_dl_self_refinement_operator_metrics_json",
                    )
                with _sr_metrics_dl_csv_col:
                    if _sr_metrics_csv:
                        st.download_button(
                            label="Download self-refinement operator metrics CSV",
                            data=_sr_metrics_csv.encode("utf-8"),
                            file_name=(
                                "hermes_self_refinement_operator_metrics_"
                                f"{_sr_metrics_slug}_{_ts}.csv"
                            ),
                            mime="text/csv; charset=utf-8",
                            key="hermes_dl_self_refinement_operator_metrics_csv",
                        )
            _sr_expl = self_refinement_workflow_explainer_payload(_iroot, workflow_profile=_wf_pick)
            _sr_ver_cap = self_refinement_timeline_policy_version_caption(_sr, _sr_expl)
            if _sr_ver_cap:
                st.caption(_sr_ver_cap)
            with st.expander("Self-refinement workflow explainer (read-only)", expanded=False):
                for cap_fn in (
                    self_refinement_workflow_yaml_raw_type_caption,
                    self_refinement_policy_yaml_file_bytes_caption,
                    self_refinement_policy_yaml_disk_version_caption,
                    self_refinement_merged_version_caption,
                    self_refinement_merged_description_preview_caption,
                    self_refinement_ungated_loop_env_gate_caption,
                    self_refinement_would_emit_marker_caption,
                    self_refinement_would_emit_after_env_caption,
                ):
                    cap = cap_fn(_sr_expl)
                    if cap:
                        st.caption(cap)
                _sr_expl_rows = self_refinement_explainer_table_rows(_sr_expl)
                if _sr_expl_rows:
                    st.dataframe(_sr_expl_rows, use_container_width=True, hide_index=True)
                _sr_expl_metrics = self_refinement_workflow_explainer_operator_metrics(_sr_expl)
                _sr_expl_metrics_cap = (
                    self_refinement_workflow_explainer_operator_metrics_caption(_sr_expl_metrics)
                )
                if _sr_expl_metrics_cap:
                    st.caption(_sr_expl_metrics_cap)
                _sr_expl_metric_rows = (
                    self_refinement_workflow_explainer_operator_metrics_table_rows(
                        _sr_expl_metrics,
                    )
                )
                if _sr_expl_metric_rows:
                    st.dataframe(
                        _sr_expl_metric_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                    _sr_expl_metrics_json = (
                        self_refinement_workflow_explainer_operator_metrics_export_json(
                            _sr_expl_metrics,
                        )
                    )
                    _sr_expl_metrics_csv = (
                        self_refinement_workflow_explainer_operator_metrics_table_rows_csv(
                            _sr_expl_metric_rows,
                        )
                    )
                    _sr_expl_metrics_slug = (
                        self_refinement_workflow_explainer_operator_metrics_export_filename_slug()
                    )
                    _sr_expl_dl_json_col, _sr_expl_dl_csv_col = st.columns(2)
                    with _sr_expl_dl_json_col:
                        st.download_button(
                            label="Download self-refinement explainer metrics JSON",
                            data=_sr_expl_metrics_json.encode("utf-8"),
                            file_name=f"hermes_{_sr_expl_metrics_slug}_{_ts}.json",
                            mime="application/json",
                            key="hermes_dl_self_refinement_explainer_metrics_json",
                        )
                    with _sr_expl_dl_csv_col:
                        if _sr_expl_metrics_csv:
                            st.download_button(
                                label="Download self-refinement explainer metrics CSV",
                                data=_sr_expl_metrics_csv.encode("utf-8"),
                                file_name=f"hermes_{_sr_expl_metrics_slug}_{_ts}.csv",
                                mime="text/csv; charset=utf-8",
                                key="hermes_dl_self_refinement_explainer_metrics_csv",
                            )
                with st.expander("Raw self-refinement explainer JSON", expanded=False):
                    st.json(_sr_expl)
            _sr_csv = self_refinement_latest_summary_rows_csv(_sr_rows)
            _sr_json = self_refinement_latest_export_json(_sr)
            _sr_tl_slug = self_refinement_latest_export_filename_slug(run_id.strip())
            _sr_dl_col, _sr_dl_json_col = st.columns(2)
            with _sr_dl_col:
                st.download_button(
                    label="Download self-refinement timeline CSV",
                    data=_sr_csv.encode("utf-8"),
                    file_name=f"hermes_self_refinement_timeline_{_sr_tl_slug}_{_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_self_refinement_timeline_csv",
                )
            with _sr_dl_json_col:
                st.download_button(
                    label="Download self-refinement timeline JSON",
                    data=_sr_json.encode("utf-8"),
                    file_name=f"hermes_self_refinement_timeline_{_sr_tl_slug}_{_ts}.json",
                    mime="application/json",
                    key="hermes_dl_self_refinement_timeline_json",
                )
            with st.expander("Raw self_refinement JSON", expanded=False):
                st.json(_sr)
