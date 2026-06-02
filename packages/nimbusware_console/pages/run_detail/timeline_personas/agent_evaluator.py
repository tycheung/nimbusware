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


def _render_agent_evaluator(run_id: str, data: dict) -> None:
    _wf_pick = _workflow_profile_pick(data)
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _slug = _run_slug(run_id.strip())

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
                            f"hermes_agent_evaluator_operator_metrics_{_ae_metrics_slug}_{_ts}.json"
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
