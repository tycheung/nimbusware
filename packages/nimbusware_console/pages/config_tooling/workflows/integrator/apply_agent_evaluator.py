from __future__ import annotations

from pathlib import Path

import streamlit as st

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_apply_agent_evaluator_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    with st.expander("Apply agent_evaluator to disk", expanded=False):
        st.caption(
            "Merges the pasted ``agent_evaluator`` block into the **selected** workflow profile "
            "via ``atomic_write_yaml`` (other YAML keys preserved). Accepts a full workflow root "
            "with ``agent_evaluator:`` or a flat ``enabled`` / ``persona_id`` map. Requires "
            f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}=1`` (or true/yes/on) in the Streamlit process env. "
            "Uses the **same** profile-stem confirmation field as **fo132** above."
        )
        st.text_area(
            "Optional pasted ``agent_evaluator`` YAML (full workflow with key, or flat mapping)",
            height=120,
            placeholder="agent_evaluator:\n  enabled: true\n  persona_id: default\n",
            key="hermes_integrator_paste_agent_evaluator_yaml",
        )
        if st.button("Dry-run merge (no write)", key="hermes_integrator_ae_dry_run_btn"):
            if not workflow_profile:
                st.error("Select a workflow profile first.")
            else:
                _mrg_ae, _b4_ae, _af_ae, _merr_ae = prepare_agent_evaluator_apply(
                    repo_root,
                    profile_stem=str(workflow_profile),
                    pasted_yaml=str(
                        st.session_state.get("hermes_integrator_paste_agent_evaluator_yaml", ""),
                    ),
                )
                st.session_state[rl.rl._LAST_AGENT_EVALUATOR_MERGE_DRY] = {
                    "profile": str(workflow_profile),
                    "before_ae": _b4_ae,
                    "after_ae": _af_ae,
                    "errors": _merr_ae,
                    "merged_ok": _mrg_ae is not None,
                }
        _dry_ae = st.session_state.get(rl._LAST_AGENT_EVALUATOR_MERGE_DRY)
        if isinstance(_dry_ae, dict) and _dry_ae.get("merged_ok"):
            st.caption("Dry-run ``agent_evaluator`` (before → after)")
            _ac1, _ac2 = st.columns(2)
            with _ac1:
                st.json(_dry_ae.get("before_ae"))
            with _ac2:
                st.json(_dry_ae.get("after_ae"))
        elif isinstance(_dry_ae, dict) and _dry_ae.get("errors"):
            for _me_ae in _dry_ae["errors"]:
                st.warning(str(_me_ae))
        _confirm_ae = str(st.session_state.get("hermes_integrator_confirm_profile", "")).strip()
        _can_apply_ae = bool(
            _integrator_write_ok
            and workflow_profile
            and _confirm_ae
            and _confirm_ae == str(workflow_profile).strip(),
        )
        if st.button(
            "Apply agent_evaluator merge to disk",
            disabled=not _can_apply_ae,
            key="hermes_integrator_ae_apply_disk_btn",
        ):
            _ok_ae, _merged_ae, _ap_errs_ae = apply_agent_evaluator_yaml(
                repo_root,
                profile_stem=str(workflow_profile),
                pasted_yaml=str(
                    st.session_state.get("hermes_integrator_paste_agent_evaluator_yaml", ""),
                ),
                confirm_profile_stem=_confirm_ae,
            )
            if _ok_ae:
                st.success("Wrote workflow YAML.")
                st.session_state.pop(rl._LAST_AGENT_EVALUATOR_MERGE_DRY, None)
            else:
                for _ap_e_ae in _ap_errs_ae:
                    st.error(str(_ap_e_ae))
