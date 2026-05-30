from __future__ import annotations

import os

import streamlit as st

from nimbusware_console.pages import _state as rl
from nimbusware_console.pages.run_detail.actions import render_run_detail_actions
from nimbusware_console.pages.run_detail.critic_matrix import render_run_detail_critic_matrix
from nimbusware_console.pages.run_detail.findings import render_run_detail_findings
from nimbusware_console.pages.run_detail.summary import render_run_detail_summary
from nimbusware_console.pages.run_detail.timeline_core import render_run_detail_timeline_core
from nimbusware_console.pages.run_detail.timeline_escalation import (
    render_run_detail_timeline_escalation,
)
from nimbusware_console.pages.run_detail.timeline_integrator import (
    render_run_detail_timeline_integrator,
)
from nimbusware_console.pages.run_detail.timeline_misc import render_run_detail_timeline_misc
from nimbusware_console.pages.run_detail.timeline_personas import (
    render_run_detail_timeline_personas,
)
from nimbusware_console.settings import API_BASE


def render_run_detail_section() -> None:
    st.divider()
    with st.container(border=True):
        st.subheader("Run detail")
        run_id = st.text_input("Run ID (detail)", placeholder="uuid", key=rl._SS_DETAIL)

        if run_id.strip():
            rid = run_id.strip()
            maker_url = os.environ.get("NIMBUSWARE_MAKER_URL", "http://127.0.0.1:8501").rstrip("/")
            st.link_button(
                "Open in Maker Review",
                f"{maker_url}/?run_id={rid}",
                help="Opens the Maker app with this run selected.",
            )
            st.markdown(
                "Artifact-style **read-only JSON** (existing API; no separate artifact store yet):"
            )
            st.caption("Copy full URL from a line below (select text or use your terminal).")
            st.code(f"{API_BASE}/runs/{rid}", language=None)
            st.code(f"{API_BASE}/runs/{rid}/timeline", language=None)
            st.code(f"{API_BASE}/runs/{rid}/findings", language=None)

        c1, c2 = st.columns(2)
        with c1:
            render_run_detail_summary(run_id)
            timeline_ctx = render_run_detail_timeline_core(run_id)
            if timeline_ctx is not None:
                data, events = timeline_ctx
                render_run_detail_timeline_integrator(run_id, data)
                render_run_detail_timeline_personas(run_id, data)
                render_run_detail_timeline_escalation(run_id, data)
                render_run_detail_timeline_misc(run_id, data)
                render_run_detail_critic_matrix(run_id, events)
        with c2:
            render_run_detail_findings(run_id)

        render_run_detail_actions(run_id)
