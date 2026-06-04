from __future__ import annotations

import streamlit as st

from nimbusware_client.http import HTTPError, get_json, post_json
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_env.env_flags import env_str


def render_hardware_panel() -> None:
    st.subheader("Hardware & resource governor")
    if st.button("Rescan hardware", key="admin_hw_rescan"):
        try:
            post_json("/platform/hardware/rescan", {})
            st.success("Hardware profile refreshed.")
            st.rerun()
        except HTTPError as exc:
            render_api_error(exc)
    try:
        data = get_json("/platform/hardware")
    except HTTPError as exc:
        render_api_error(exc)
        return
    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    gov = data.get("resource_governor") if isinstance(data.get("resource_governor"), dict) else {}
    st.markdown(f"**Tier:** `{profile.get('tier', '?')}`")
    cols = st.columns(3)
    cols[0].metric("RAM total (GB)", profile.get("ram_total_gb") or "—")
    cols[1].metric("RAM avail (GB)", profile.get("ram_available_gb") or "—")
    cols[2].metric("CPU cores", profile.get("cpu_count") or "—")
    st.markdown("**Effective governor limits**")
    st.json(gov)
    ranked = data.get("models_ranked")
    if isinstance(ranked, list) and ranked:
        st.dataframe(ranked[:10], use_container_width=True)
    from nimbusware_env.edition import is_enterprise

    if is_enterprise():
        host = st.text_input(
            "SSH remote host (enterprise)",
            value=env_str("NIMBUSWARE_HW_SSH_HOST"),
            key="admin_hw_ssh_host",
        )
        if st.button("Probe remote host", key="admin_hw_ssh_probe"):
            if not host.strip():
                st.warning("Enter a remote host first.")
            else:
                try:
                    remote_data = get_json(
                        "/platform/hardware",
                        params={"remote_host": host.strip()},
                    )
                    remote_profile = (
                        remote_data.get("profile")
                        if isinstance(remote_data.get("profile"), dict)
                        else {}
                    )
                    st.success(f"Remote tier: `{remote_profile.get('tier', '?')}`")
                    st.json(remote_profile)
                except HTTPError as exc:
                    render_api_error(exc)
        st.caption(
            "Set NIMBUSWARE_HW_SSH_MOCK=1 for mock probe, or configure "
            "NIMBUSWARE_HW_SSH_IDENTITY for live SSH."
        )
