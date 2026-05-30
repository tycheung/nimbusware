from __future__ import annotations

import os

import streamlit as st

from nimbusware_maker.api_client import get_json


def render_settings_panel() -> None:
    st.subheader("Settings")
    st.caption("Workspace preferences for this machine. Admin-only routing lives in the Admin Console.")

    auto_advance = os.environ.get("HERMES_SLICE_AUTO_ADVANCE", "0").strip()
    st.markdown(
        f"**Auto-advance slices:** `{auto_advance or '0'}` "
        "(set `HERMES_SLICE_AUTO_ADVANCE=1` in `.env` to chain slices without pauses)",
    )

    try:
        readiness = get_json("/platform/readiness")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load readiness presets: {exc}")
        return

    presets = readiness.get("presets")
    if not isinstance(presets, dict):
        return

    st.markdown("**Model presets** (from local readiness)")
    for key, preset in presets.items():
        if not isinstance(preset, dict):
            continue
        label = str(preset.get("label") or key)
        hint = str(preset.get("hint") or "")
        st.markdown(f"- **{label}** — {hint}")
