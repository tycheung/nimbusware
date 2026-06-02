from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import platform as platform_svc
from nimbusware_maker.ui.hardware_settings import render_hardware_settings_panel
from nimbusware_maker.ui.ollama_models import render_ollama_models_panel
from nimbusware_maker.ui.operator_settings import render_operator_settings_panel


def render_settings_panel() -> None:
    st.subheader("Settings")
    st.caption(
        "Workspace preferences for this machine. Admin-only routing lives in the Admin Console."
    )

    render_operator_settings_panel()
    st.divider()

    try:
        readiness = platform_svc.fetch_readiness()
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load readiness presets: {exc}")
        return

    presets = readiness.get("presets")
    if not isinstance(presets, dict):
        return

    st.divider()
    render_hardware_settings_panel()
    st.divider()
    render_ollama_models_panel()
    st.divider()

    st.markdown("**Model presets** (from local readiness)")
    for key, preset in presets.items():
        if not isinstance(preset, dict):
            continue
        label = str(preset.get("label") or key)
        hint = str(preset.get("hint") or "")
        st.markdown(f"- **{label}** — {hint}")
