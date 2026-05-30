from __future__ import annotations

from pathlib import Path

from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403


def render_integrator_preview_section(*, repo_root: Path, workflow_profile: str | None) -> None:
    st.text_input(
        "Bundle id (catalog ``bundles[].id``)",
        value="auth-rbac-starter",
        key="hermes_integrator_bundle_id",
    )
    st.text_area(
        "Synthetic ``tags`` JSON array (optional; overrides workflow ``project_tags`` when set)",
        value="[]",
        height=68,
        key="hermes_integrator_tags_json",
    )
    if st.button("Run integrator preview", key="hermes_integrator_preview_btn"):
        try:
            st.session_state[rl._LAST_INTEGRATOR_PREVIEW] = integrator_preview_payload(
                repo_root,
                workflow_profile=workflow_profile,
                pasted_yaml=str(st.session_state.get("hermes_integrator_paste_yaml", "")),
                bundle_id=str(st.session_state.get("hermes_integrator_bundle_id", "")),
                synthetic_tags_json=str(
                    st.session_state.get("hermes_integrator_tags_json", "[]"),
                ),
            )
        except (OSError, ValueError) as _ix_exc:
            st.session_state.pop(rl._LAST_INTEGRATOR_PREVIEW, None)
            st.error(f"Preview failed: {_ix_exc}")
    _ip = st.session_state.get(rl._LAST_INTEGRATOR_PREVIEW)
    if isinstance(_ip, dict):
        _rows = [
            {"field": "workflow_profile", "value": str(_ip.get("workflow_profile"))},
            {
                "field": "disk integrator_gate.enabled",
                "value": str(_ip.get("disk_integrator_gate_enabled")),
            },
            {
                "field": "thresholds.yaml enabled (catalog)",
                "value": str(_ip.get("catalog_thresholds_enabled")),
            },
            {
                "field": "pasted enabled (preview only)",
                "value": str(_ip.get("pasted_enabled_preview")),
            },
            {
                "field": "effective min_score_to_pass",
                "value": str(_ip.get("effective_min_score_to_pass")),
            },
            {"field": "bundle_id", "value": str(_ip.get("bundle_id"))},
            {"field": "score_fit", "value": str(_ip.get("score_fit"))},
            {"field": "passes_gate", "value": str(_ip.get("passes_gate"))},
        ]
        _iperr = _ip.get("validation_errors")
        if isinstance(_iperr, list) and _iperr:
            for _e in _iperr:
                st.warning(str(_e))
        st.dataframe(_rows, use_container_width=True, hide_index=True)
        with st.expander("Raw integrator preview JSON", expanded=False):
            st.json(_ip)
    _integrator_write_ok = workflow_yaml_write_enabled()
    st.caption(
        "Workflow YAML disk writes (**fo132** ``integrator_gate``, "
        "**fo140** ``agent_evaluator``, **§14 #13** full-profile merge): "
        f"``{ALLOW_WORKFLOW_YAML_WRITE_ENV}`` is "
        f"{'**enabled**' if _integrator_write_ok else '**disabled** — no disk writes'}."
    )
    st.text_input(
        "Confirm profile stem for disk apply (type exactly the selected workflow profile)",
        key="hermes_integrator_confirm_profile",
    )
