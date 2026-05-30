from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from nimbusware_console.console_theme import (
    streamlit_theme_defaults_caption,
    streamlit_white_label_deferred_caption,
)
from nimbusware_console.pages.config_tooling import render_config_tooling_section
from nimbusware_console.pages.run_detail import render_run_detail_section
from nimbusware_console.pages import _state as rl
from nimbusware_console.pages.run_list import render_run_list_section
from nimbusware_console.settings import API_BASE, repo_root


def render_main() -> None:
    st.title("Nimbusware Admin Console")
    st.caption(streamlit_theme_defaults_caption(repo_root=repo_root()))
    st.caption(streamlit_white_label_deferred_caption())

    _repo_for_ui = repo_root()
    with st.sidebar:
        from nimbusware_console.custom_agents_ui import render_custom_agents_sidebar
        from nimbusware_console.enterprise_console_ui import render_enterprise_sidebar

        render_custom_agents_sidebar(_repo_for_ui)
        _hermes_enterprise_console_active = render_enterprise_sidebar()

    with st.container():
        from nimbusware_console.operator_chat import render_operator_chat

        render_operator_chat(repo_root=_repo_for_ui)
        st.divider()

    if _hermes_enterprise_console_active:
        from nimbusware_console.enterprise_console_ui import render_enterprise_fleet_dashboard

        render_enterprise_fleet_dashboard()

    rl._run_list_ensure_defaults()
    if rl._SS_DETAIL not in st.session_state:
        st.session_state[rl._SS_DETAIL] = ""
    _qp_warnings: list[str] = []
    rl._run_list_qp_apply_to_session(_qp_warnings)
    for _msg in _qp_warnings:
        st.warning(_msg)
    if st.session_state.get(rl._LAST_LIST_ERR):
        st.warning(f"Last list fetch failed: {st.session_state[rl._LAST_LIST_ERR]}")

    render_config_tooling_section()
    render_run_list_section()
    st.divider()
    render_run_detail_section()
