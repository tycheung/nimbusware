from __future__ import annotations

import os

import streamlit as st

from nimbusware_maker.services import hardware as hw_svc


def render_hardware_settings_panel() -> None:
    st.markdown("**Hardware & resource governor**")
    try:
        data = hw_svc.fetch_hardware()
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load hardware profile: {exc}")
        return

    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    governor = (
        data.get("resource_governor") if isinstance(data.get("resource_governor"), dict) else {}
    )
    tier = str(profile.get("tier") or "unknown")
    st.caption(f"Detected tier: **{tier}**")
    ram_avail = profile.get("ram_available_gb")
    if ram_avail is not None:
        st.caption(f"Available RAM: {ram_avail} GB")

    ram_pct = st.slider(
        "Max system RAM %",
        min_value=50,
        max_value=95,
        value=int(governor.get("max_system_ram_pct") or 75),
        key="maker_hw_ram_pct",
    )
    auto_adjust = st.toggle(
        "Auto-adjust slice budgets to hardware",
        value=bool(governor.get("auto_adjust", True)),
        key="maker_hw_auto_adjust",
    )
    os.environ["NIMBUSWARE_MAX_SYSTEM_RAM_PCT"] = str(ram_pct)
    os.environ["NIMBUSWARE_HW_AUTO_ADJUST"] = "1" if auto_adjust else "0"

    if st.button("Rescan hardware", key="maker_hw_rescan"):
        try:
            hw_svc.rescan_hardware()
            st.success("Hardware profile refreshed.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
