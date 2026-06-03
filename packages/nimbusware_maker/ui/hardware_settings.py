from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import hardware as hw_svc
from nimbusware_maker.services import operator_settings as settings_svc


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

    preset_options = ("tiny", "standard", "careful")
    try:
        settings = settings_svc.fetch_user_settings()
        values = settings.get("values") if isinstance(settings.get("values"), dict) else {}
        current_preset = str(values.get("HERMES_SLICE_BUDGET_PRESET", "standard")).lower()
    except Exception:  # noqa: BLE001
        current_preset = "standard"
    if current_preset not in preset_options:
        current_preset = "standard"
    preset = st.selectbox(
        "Slice budget preset",
        preset_options,
        index=preset_options.index(current_preset),
        key="maker_slice_budget_preset",
        help="tiny: 1 file / 40 LOC; standard: 3 / 120; careful: 2 / 80 with more replans",
    )

    if st.button("Save hardware governor", key="maker_hw_save"):
        try:
            settings_svc.patch_user_settings(
                {
                    "NIMBUSWARE_MAX_SYSTEM_RAM_PCT": str(ram_pct),
                    "NIMBUSWARE_HW_AUTO_ADJUST": "1" if auto_adjust else "0",
                    "HERMES_SLICE_BUDGET_PRESET": preset,
                },
            )
            st.success("Hardware governor settings saved.")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    if st.button("Rescan hardware", key="maker_hw_rescan"):
        try:
            hw_svc.rescan_hardware()
            st.success("Hardware profile refreshed.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
