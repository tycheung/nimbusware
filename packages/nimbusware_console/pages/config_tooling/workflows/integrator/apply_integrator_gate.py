from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_apply_integrator_gate_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Apply integrator_gate to disk", expanded=False):
        st.caption(
            "Merges the pasted ``integrator_gate`` block into the **selected** workflow profile "
            "via ``atomic_write_yaml`` (other YAML keys preserved). Requires "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on) in the Streamlit process env."
        )
        if st.button("Dry-run merge (no write)", key="hermes_integrator_dry_run_btn"):
            if not workflow_profile:
                st.error("Select a workflow profile first.")
            else:
                _mrg, _b4, _af, _merr = prepare_integrator_gate_apply(
                    repo_root,
                    profile_stem=str(workflow_profile),
                    pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                )
                st.session_state[rl.rl._LAST_INTEGRATOR_MERGE_DRY] = {
                    "profile": str(workflow_profile),
                    "before_gate": _b4,
                    "after_gate": _af,
                    "errors": _merr,
                    "merged_ok": _mrg is not None,
                }
        _dry = st.session_state.get(rl._LAST_INTEGRATOR_MERGE_DRY)
        if isinstance(_dry, dict) and _dry.get("merged_ok"):
            st.caption("Dry-run ``integrator_gate`` (before → after)")
            _c1, _c2 = st.columns(2)
            with _c1:
                st.json(_dry.get("before_gate"))
            with _c2:
                st.json(_dry.get("after_gate"))
        elif isinstance(_dry, dict) and _dry.get("errors"):
            for _me in _dry["errors"]:
                st.warning(str(_me))
        _confirm = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
        _can_apply = bool(
            _integrator_write_ok
            and workflow_profile
            and _confirm
            and _confirm == str(workflow_profile).strip(),
        )
        if st.button(
            "Apply merge to disk",
            disabled=not _can_apply,
            key="hermes_integrator_apply_disk_btn",
        ):
            _ok_ap, _merged_doc, _ap_errs = apply_integrator_gate_yaml(
                repo_root,
                profile_stem=str(workflow_profile),
                pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                confirm_profile_stem=_confirm,
            )
            if _ok_ap:
                st.success("Wrote workflow YAML.")
                st.session_state.pop(rl._LAST_INTEGRATOR_MERGE_DRY, None)
            else:
                for _ap_e in _ap_errs:
                    st.error(str(_ap_e))
