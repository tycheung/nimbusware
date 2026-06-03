from __future__ import annotations

import streamlit as st

from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_env.env_flags import env_str

SESSION_ADMIN_UNLOCKED = "maker_admin_unlocked"


def is_admin_unlocked(session_state: object | None = None) -> bool:
    state = session_state if session_state is not None else st.session_state
    get = getattr(state, "get", None)
    if not callable(get):
        return False
    return bool(get(SESSION_ADMIN_UNLOCKED))


def clear_admin_unlock(session_state: object | None = None) -> None:
    state = session_state if session_state is not None else st.session_state
    setattr(state, SESSION_ADMIN_UNLOCKED, False)


def admin_console_url() -> str:
    return env_str("NIMBUSWARE_ADMIN_CONSOLE_URL", default="http://127.0.0.1:8502").rstrip("/")


def render_admin_sidebar() -> None:
    st.sidebar.divider()
    st.sidebar.caption("Admin")
    if is_admin_unlocked():
        st.sidebar.success("Signed in as admin")
        st.sidebar.link_button("Open Admin Console", admin_console_url(), use_container_width=True)
        st.sidebar.caption("Run `nimbusware-admin` if the link does not load.")
        if st.sidebar.button("Sign out", key="maker_admin_sign_out"):
            clear_admin_unlock()
            st.rerun()
        return

    with st.sidebar.expander("Sign in as admin", expanded=False):
        token = st.text_input("Admin token", type="password", key="maker_admin_token_input")
        if st.button("Unlock admin tools", key="maker_admin_unlock"):
            if token == nimbusware_admin_token():
                st.session_state[SESSION_ADMIN_UNLOCKED] = True
                st.rerun()
            else:
                st.error("Invalid admin token.")
