from __future__ import annotations

import streamlit as st

from nimbusware_maker.session import is_admin_unlocked, render_admin_sidebar
from nimbusware_maker.ui.approval import render_approval_panel
from nimbusware_maker.ui.home import render_projects_panel, render_readiness_strip
from nimbusware_maker.ui.intent import render_intent_wizard
from nimbusware_maker.ui.model_manager import render_model_manager_panel
from nimbusware_maker.ui.progress import render_progress_panel
from nimbusware_maker.ui.run_theater import render_run_theater_panel
from nimbusware_maker.ui.settings import render_settings_panel
from nimbusware_maker.ui.wizard import render_first_run_wizard


def _apply_deep_link_params() -> None:
    params = st.query_params
    run_id = str(params.get("run_id") or "").strip()
    project_id = str(params.get("project_id") or "").strip()
    if run_id:
        st.session_state["maker_active_run_id"] = run_id
    if project_id:
        st.session_state["maker_active_project_id"] = project_id


def render_main() -> None:
    _apply_deep_link_params()

    st.title("Nimbusware Maker")
    st.caption(
        "Describe what you want → review small changes → keep or revert. "
        "Simple mode hides operator telemetry.",
    )

    render_admin_sidebar()

    admin_unlocked = is_admin_unlocked()
    mode_options = ["Simple", "Advanced"] if admin_unlocked else ["Simple"]
    mode = st.sidebar.radio("Mode", mode_options, index=0)
    simple_mode = mode == "Simple"
    if admin_unlocked and not simple_mode:
        st.sidebar.caption(
            "Advanced mode shows extra diagnostics. Admin Console has full ops tooling."
        )

    st.sidebar.caption(
        "Agent tools: set `HERMES_SLICE_IMPLEMENT=agent` and `HERMES_USE_LLM=1` for tool-using slices.",
    )

    tabs = ["Home", "Build", "Review", "Progress", "Models", "Settings"]
    tab_home, tab_build, tab_review, tab_progress, tab_models, tab_settings = st.tabs(tabs)
    with tab_home:
        if not render_first_run_wizard():
            render_readiness_strip()
            st.divider()
            render_projects_panel()
    with tab_build:
        render_intent_wizard()
    with tab_review:
        render_approval_panel()
    with tab_progress:
        render_run_theater_panel()
        st.divider()
        render_progress_panel(simple_mode=simple_mode)
    with tab_models:
        render_model_manager_panel()
    with tab_settings:
        render_settings_panel()


__all__ = ["render_main"]
