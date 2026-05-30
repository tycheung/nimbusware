from __future__ import annotations

import streamlit as st

from nimbusware_env.admin_token import nimbusware_admin_token

SESSION_AUTHENTICATED = "admin_console_authenticated"


def require_admin_session() -> None:
    if st.session_state.get(SESSION_AUTHENTICATED):
        return

    st.title("Nimbusware Admin Console")
    st.caption("Sign in with your admin token to open the control plane.")
    token = st.text_input("Admin token", type="password", key="admin_console_token")
    if st.button("Sign in", key="admin_console_sign_in"):
        if token == nimbusware_admin_token():
            st.session_state[SESSION_AUTHENTICATED] = True
            st.rerun()
        else:
            st.error("Invalid admin token.")
    st.stop()
