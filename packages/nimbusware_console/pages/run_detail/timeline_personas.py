"""Run detail — persona assignment, agent evaluator, self-refinement panels."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


def _workflow_profile_pick(data: dict[str, Any]) -> str:
    wf = data.get("workflow_profile") if isinstance(data, dict) else None
    if isinstance(wf, str) and wf.strip():
        return wf.strip()
    return os.environ.get("HERMES_WORKFLOW_PROFILE", "nimbusware_production")


def render_run_detail_timeline_personas(run_id: str, data: dict) -> None:
    _wf_pick = _workflow_profile_pick(data)

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
                agent_evaluator_auto_actions_caption,
            ):
                cap = cap_fn(_ae)
                if cap:
                    st.caption(cap)
            st.dataframe(_ae_rows, use_container_width=True)
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
            for cap_fn, arg in (
                (self_refinement_version_attempt_caption, _sr),
                (self_refinement_evaluation_caption, _sr),
                (self_refinement_ungated_loop_caption, _sr),
            ):
                cap = cap_fn(arg)
                if cap:
                    st.caption(cap)
            st.dataframe(_sr_rows, use_container_width=True)
            _sr_expl = self_refinement_workflow_explainer_payload(
                Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve(),
                workflow_profile=_wf_pick,
            )
            _sr_ver_cap = self_refinement_timeline_policy_version_caption(_sr, _sr_expl)
            if _sr_ver_cap:
                st.caption(_sr_ver_cap)
            with st.expander("Raw self_refinement JSON", expanded=False):
                st.json(_sr)
