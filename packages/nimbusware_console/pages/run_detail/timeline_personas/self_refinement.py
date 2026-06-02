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


def _render_self_refinement(run_id: str, data: dict) -> None:
    _wf_pick = _workflow_profile_pick(data)
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _slug = _run_slug(run_id.strip())
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
                            f"hermes_self_refinement_operator_metrics_{_sr_metrics_slug}_{_ts}.json"
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
                _sr_expl_metrics_cap = self_refinement_workflow_explainer_operator_metrics_caption(
                    _sr_expl_metrics
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
