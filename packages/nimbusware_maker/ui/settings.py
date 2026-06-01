from __future__ import annotations

import streamlit as st

from nimbusware_env.env_flags import hermes_slice_auto_advance_enabled
from nimbusware_maker.api_client import get_json
from nimbusware_maker.ui.ollama_models import render_ollama_models_panel


def render_settings_panel() -> None:
    st.subheader("Settings")
    st.caption("Workspace preferences for this machine. Admin-only routing lives in the Admin Console.")

    enabled = hermes_slice_auto_advance_enabled()
    auto_advance = "1" if enabled else "0"
    st.markdown(
        f"**Auto-advance slices:** `{auto_advance}` "
        "(set `HERMES_SLICE_AUTO_ADVANCE=0` in `.env` to pause between slices)",
    )

    try:
        readiness = get_json("/platform/readiness")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load readiness presets: {exc}")
        return

    presets = readiness.get("presets")
    if not isinstance(presets, dict):
        return

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
