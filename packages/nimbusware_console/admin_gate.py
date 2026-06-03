from __future__ import annotations

import streamlit as st

from nimbusware_env.admin_token import nimbusware_admin_token
from nimbusware_env.oidc_config import load_oidc_config, oidc_required_for_console

SESSION_AUTHENTICATED = "admin_console_authenticated"
SESSION_OIDC_STATE = "admin_oidc_state"
SESSION_OIDC_VERIFIER = "admin_oidc_code_verifier"


def _try_oidc_callback() -> bool:
    params = st.query_params
    code = params.get("code")
    state = params.get("state")
    if not code:
        return False
    from nimbusware_console.services.oauth_pkce import accept_oidc_callback

    ok, detail = accept_oidc_callback(
        code=code if isinstance(code, str) else None,
        state=state if isinstance(state, str) else None,
        expected_state=str(st.session_state.get(SESSION_OIDC_STATE, "")),
        code_verifier=str(st.session_state.get(SESSION_OIDC_VERIFIER, "")),
    )
    if ok:
        st.session_state[SESSION_AUTHENTICATED] = True
        st.session_state.pop(SESSION_OIDC_STATE, None)
        st.session_state.pop(SESSION_OIDC_VERIFIER, None)
        st.query_params.clear()
        st.rerun()
    st.error(f"OIDC sign-in failed: {detail}")
    return True


def _render_oidc_login() -> None:
    config = load_oidc_config()
    st.title("Nimbusware Admin Console")
    st.caption("Enterprise SSO — API calls still use server-side admin token or API keys.")
    if st.button("Sign in with SSO", key="admin_oidc_sign_in"):
        from nimbusware_console.services.oauth_pkce import build_authorize_url

        challenge = build_authorize_url(config)
        st.session_state[SESSION_OIDC_STATE] = challenge.state
        st.session_state[SESSION_OIDC_VERIFIER] = challenge.code_verifier
        st.markdown(f"[Continue to IdP]({challenge.authorize_url})")
    st.divider()
    st.caption("Local fallback (dev)")
    token = st.text_input("Admin token", type="password", key="admin_console_token_oidc")
    if st.button("Sign in with token", key="admin_console_sign_in_oidc"):
        if token == nimbusware_admin_token():
            st.session_state[SESSION_AUTHENTICATED] = True
            st.rerun()
        else:
            st.error("Invalid admin token.")
    st.stop()


def require_admin_session() -> None:
    if st.session_state.get(SESSION_AUTHENTICATED):
        return

    if _try_oidc_callback():
        st.stop()

    if oidc_required_for_console():
        _render_oidc_login()
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
