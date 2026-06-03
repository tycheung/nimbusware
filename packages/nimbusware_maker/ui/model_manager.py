from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import hardware as hw_svc
from nimbusware_maker.services import models as models_svc
from nimbusware_maker.wizard_model import fit_level_caption


def render_model_manager_panel() -> None:
    st.subheader("Model Manager")
    gpu_only = st.toggle("GPU-only ranking", value=False, key="mm_gpu_only")
    gpu_group_index = st.number_input("GPU group index", min_value=0, value=0, step=1)
    use_case = st.selectbox("Use case", ["coding", "chat", "general"], index=0)
    try:
        hw = hw_svc.fetch_hardware()
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Hardware: {exc}")
        hw = {}
    profile = hw.get("profile") if isinstance(hw.get("profile"), dict) else {}
    st.caption(
        f"Tier **{profile.get('tier', '?')}** — RAM avail {profile.get('ram_available_gb', '?')} GB"
    )
    if st.button("Rescan", key="mm_rescan"):
        try:
            hw_svc.rescan_hardware()
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
    try:
        deps = models_svc.fetch_model_dependencies()
        if not deps.get("ollama_reachable"):
            st.warning(deps.get("ollama_message") or "Ollama not reachable")
        if deps.get("docker_gpu_warning"):
            st.caption(str(deps["docker_gpu_warning"]))
    except Exception:
        pass
    try:
        ranked_body = models_svc.fetch_models_ranked(
            use_case=use_case,
            gpu_only=gpu_only,
            gpu_group_index=int(gpu_group_index),
        )
        models = ranked_body.get("models") if isinstance(ranked_body.get("models"), list) else []
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load ranked models: {exc}")
        return
    if not models:
        st.info("No models in allowlist.")
        return
    for row in models[:15]:
        if not isinstance(row, dict):
            continue
        mid = str(row.get("model_id") or "")
        fit = str(row.get("fit_level") or "")
        with st.expander(f"{mid} — {fit}", expanded=False):
            st.caption(fit_level_caption(fit))
            st.json(
                {k: row[k] for k in ("run_mode", "required_gb", "score", "presets") if k in row}
            )
            cols = st.columns(3)
            for preset, col in zip(("quality", "balanced", "speed"), cols, strict=True):
                with col:
                    if st.button(f"Apply {preset}", key=f"mm_apply_{mid}_{preset}"):
                        try:
                            out = models_svc.apply_model_preset(model_id=mid, preset=preset)
                            st.success(out.get("materialize_hint", "Applied"))
                        except Exception as exc:  # noqa: BLE001
                            st.error(str(exc))
