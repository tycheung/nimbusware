"""Maker UI package."""

from __future__ import annotations

import streamlit as st

from nimbusware_maker.ui.approval import render_approval_panel
from nimbusware_maker.ui.home import render_projects_panel, render_readiness_strip
from nimbusware_maker.ui.intent import render_intent_wizard
from nimbusware_maker.ui.progress import render_progress_panel
from nimbusware_maker.ui.wizard import render_first_run_wizard


def render_main() -> None:
    st.title("Nimbusware Maker")
    st.caption(
        "Describe what you want → review small changes → keep or revert. "
        "Simple mode hides operator telemetry.",
    )

    mode = st.sidebar.radio("Mode", ["Simple", "Advanced"], index=0)
    simple_mode = mode == "Simple"
    if not simple_mode:
        st.sidebar.markdown(
            "Advanced: run the operator console with "
            "`streamlit run packages/nimbusware_console/app.py`",
        )
    st.sidebar.caption(
        "Agent tools: set `HERMES_SLICE_IMPLEMENT=agent` and `HERMES_USE_LLM=1` for tool-using slices.",
    )

    tab_home, tab_build, tab_review, tab_progress = st.tabs(
        ["Home", "Build", "Review", "Progress"],
    )
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
        render_progress_panel(simple_mode=simple_mode)


__all__ = ["render_main"]
