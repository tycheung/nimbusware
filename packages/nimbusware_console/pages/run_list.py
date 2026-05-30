"""Recent runs list filters, fetch, and display."""

from __future__ import annotations

import streamlit as st

from nimbusware_console.pages import _state as rl
from nimbusware_console.pages.preflight_fleet import render_preflight_fleet_section
from nimbusware_console.settings import API_BASE


def render_run_list_section() -> None:
    """Render the bordered run-list block (filters, paging, optional preflight)."""
    with st.container(border=True):
        st.subheader("Recent runs")
        st.caption(
            "Run list filters sync to the page URL (bookmark/share). Other query keys are left intact.",
        )
        st.text_input("List filter: workflow_profile (optional)", key=rl._SS_WF)
        st.text_input(
            "List filter: workflow_profile_prefix (optional; only if workflow_profile empty)",
            key=rl._SS_PFX,
        )
        st.selectbox(
            "List sort order",
            options=["newest_first", "oldest_first"],
            key=rl._SS_ORDER,
        )
        st.selectbox(
            "List filter: has_escalation (optional; matches GET /v1/runs)",
            options=["(not set)", "0", "1"],
            key=rl._SS_ESC,
            help="0 = without run.escalated; 1 = with run.escalated",
        )
        st.selectbox(
            "List filter: status (optional; replay-derived: created / running / terminal)",
            options=["(not set)", "created", "running", "terminal"],
            key=rl._SS_ST,
            help="Matches GET /v1/runs?status= (same semantics as run summaries).",
        )
        st.checkbox(
            "Include per-run summaries (sets limit=20; API cap for include_summary)",
            key=rl._SS_SUM,
        )
        st.text_input(
            "List filter: created_after (ISO-8601, optional; e.g. 2020-01-01T00:00:00Z)",
            key=rl._SS_CA,
        )
        st.text_input(
            "List filter: created_before (ISO-8601, optional)",
            key=rl._SS_CB,
        )
        col_off, col_lim = st.columns(2)
        with col_off:
            st.number_input("List offset", min_value=0, step=1, key=rl._SS_OFF)
        with col_lim:
            st.number_input(
                "List limit (1–200; max 20 when summaries on)",
                min_value=1,
                max_value=200,
                step=1,
                key=rl._SS_LIM,
            )

        st.text_input(
            "Keyset cursor (optional; paste ``next_cursor`` from API JSON; "
            "clears offset paging when set)",
            key=rl._SS_CUR,
            help=(
                "When non-empty, calls GET /v1/runs with cursor= and offset=0. "
                "Clear to use numeric offset again."
            ),
        )

        _snap = st.session_state.get(rl._LAST_LIST_PAGE)
        _can_next = bool(_snap and _snap.get("has_more") and _snap.get("n_ids", 0) > 0)
        _can_prev = bool(_snap and int(_snap.get("offset", 0)) > 0)
        _nc = _snap.get("next_cursor") if isinstance(_snap, dict) else None
        _can_next_keyset = bool(
            _snap and _snap.get("has_more") and isinstance(_nc, str) and len(_nc) > 0,
        )

        col_rf, col_rs, col_nx, col_nk, col_pr = st.columns([2, 1, 1, 1, 1])
        with col_rf:
            _refresh = st.button("Refresh run list")
        with col_rs:
            _reset_list = st.button(
                "Reset list filters",
                help=(
                    "Clears list query params and session filters "
                    "(bookmark URL resets for this block)."
                ),
            )
        with col_nx:
            _next_page = st.button("Next page", disabled=not _can_next)
        with col_nk:
            _next_keyset = st.button(
                "Next (keyset)",
                disabled=not _can_next_keyset,
                help="Sets cursor from last response ``next_cursor`` (matches API keyset paging).",
            )
        with col_pr:
            _prev_page = st.button("Prev page", disabled=not _can_prev)

        st.caption(
            "Next/Prev step the list **offset** (same as API **Link** ``rel=prev/next`` when not "
            "using keyset). **Next (keyset)** applies ``next_cursor`` and clears offset; clear the "
            "cursor field to return to offset paging. Refresh once after changing filters.",
        )
        if isinstance(_snap, dict) and (
            _snap.get("link")
            or _snap.get("next_cursor")
            or (
                isinstance(_snap.get("total"), int)
                and not isinstance(_snap.get("total"), bool)
            )
        ):
            with st.expander("Pagination (API)", expanded=False):
                st.caption("RFC 5988 ``Link`` from the last successful list response (copy below).")
                st.code(str(_snap.get("link") or ""), language=None)
                st.caption(
                    "Opaque ``next_cursor`` from the JSON body (same value as **Next (keyset)**)."
                )
                st.code(str(_snap.get("next_cursor") or ""), language=None)
                _tot_snap = _snap.get("total")
                if isinstance(_tot_snap, int) and not isinstance(_tot_snap, bool):
                    st.caption(f"``total`` from the same JSON body: **{_tot_snap}** (server-reported).")

        if _refresh:
            rl._run_list_fetch_and_display()
        elif _reset_list:
            rl._run_list_reset_defaults()
            rl._run_list_clear_query_params()
            st.rerun()
        elif _next_page and _snap:
            st.session_state[rl._SS_CUR] = ""
            st.session_state[rl._SS_OFF] = int(_snap["offset"]) + int(_snap["n_ids"])
            rl._run_list_fetch_and_display()
        elif _next_keyset and _snap:
            kc = _snap.get("next_cursor")
            if isinstance(kc, str) and kc:
                st.session_state[rl._SS_CUR] = kc
                st.session_state[rl._SS_OFF] = 0
                rl._run_list_fetch_and_display()
        elif _prev_page and _snap:
            st.session_state[rl._SS_CUR] = ""
            _lim_step = int(_snap["params"].get("limit", 50))
            st.session_state[rl._SS_OFF] = max(0, int(_snap["offset"]) - _lim_step)
            rl._run_list_fetch_and_display()

    render_preflight_fleet_section()
