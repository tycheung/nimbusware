"""First-run wizard — folder, readiness, first project (fo308)."""

from __future__ import annotations

import streamlit as st

from nimbusware_maker.api_client import get_json, post_json
from nimbusware_maker.onboarding import SESSION_WIZARD_STEP, is_onboarded, mark_onboarded


def render_first_run_wizard() -> bool:
    """Return True if wizard was shown (caller may skip other home content)."""
    if is_onboarded(st.session_state):
        return False

    st.subheader("Welcome to Nimbusware Maker")
    st.markdown(
        "This short setup picks a project folder, checks local readiness, "
        "and starts your first small iteration.",
    )

    step = int(st.session_state.get(SESSION_WIZARD_STEP, 1))
    st.progress(step / 4.0)

    if step == 1:
        st.markdown("**Step 1 of 4 — Project folder**")
        project_name = st.text_input("Project name", value="My app")
        workspace_path = st.text_input(
            "Folder for your software",
            placeholder="C:/Users/you/projects/my-app",
        )
        template = st.selectbox("Start from", ["greenfield", "attach"])
        if st.button("Next", type="primary"):
            if not workspace_path.strip():
                st.error("Enter a folder path.")
            else:
                st.session_state["wizard_project"] = {
                    "name": project_name,
                    "workspace_path": workspace_path.strip(),
                    "template": template,
                }
                st.session_state[SESSION_WIZARD_STEP] = 2
                st.rerun()
        return True

    if step == 2:
        st.markdown("**Step 2 of 4 — Local readiness**")
        try:
            readiness = get_json("/platform/readiness")
            status = str(readiness.get("status") or "unknown")
            st.info(f"Platform status: {status.replace('_', ' ')}")
            checks = readiness.get("checks")
            if isinstance(checks, dict):
                for name, check in checks.items():
                    if isinstance(check, dict):
                        st.caption(f"{name}: {check.get('message', '')}")
        except Exception as exc:  # noqa: BLE001
            st.warning(
                f"Could not reach the API ({exc}). Start it with: poetry run nimbusware-api",
            )
        cols = st.columns(2)
        with cols[0]:
            if st.button("Back"):
                st.session_state[SESSION_WIZARD_STEP] = 1
                st.rerun()
        with cols[1]:
            if st.button("Next", type="primary"):
                st.session_state[SESSION_WIZARD_STEP] = 3
                st.rerun()
        return True

    if step == 3:
        st.markdown("**Step 3 of 4 — What do you want to build?**")
        business_prompt = st.text_area(
            "Business prompt",
            placeholder="A simple inventory tracker for my shop…",
            height=100,
        )
        st.session_state["wizard_business_prompt"] = business_prompt
        cols = st.columns(2)
        with cols[0]:
            if st.button("Back"):
                st.session_state[SESSION_WIZARD_STEP] = 2
                st.rerun()
        with cols[1]:
            if st.button("Next", type="primary"):
                if not business_prompt.strip():
                    st.error("Describe what you want to build.")
                else:
                    st.session_state[SESSION_WIZARD_STEP] = 4
                    st.rerun()
        return True

    if step == 4:
        st.markdown("**Step 4 of 4 — Create project and start**")
        project_cfg = st.session_state.get("wizard_project") or {}
        prompt = str(st.session_state.get("wizard_business_prompt") or "").strip()
        if st.button("Finish setup", type="primary"):
            try:
                project = post_json(
                    "/projects",
                    {
                        "name": project_cfg.get("name", "My app"),
                        "workspace_path": project_cfg.get("workspace_path", "."),
                        "template": project_cfg.get("template", "greenfield"),
                        "default_workflow_profile": "micro_slice",
                    },
                )
                run = post_json(
                    "/runs",
                    {
                        "workflow_profile": "micro_slice",
                        "project_id": project.get("project_id"),
                        "requirements": {"business_prompt": prompt, "clarifications": []},
                    },
                )
                run_id = str(run.get("run_id") or "")
                st.session_state["maker_active_project_id"] = project.get("project_id")
                st.session_state["maker_active_run_id"] = run_id
                mark_onboarded(st.session_state)
                st.session_state[SESSION_WIZARD_STEP] = 1
                st.success(f"Ready — run {run_id}. Open Review to approve your plan.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Setup failed: {exc}")
        if st.button("Back"):
            st.session_state[SESSION_WIZARD_STEP] = 3
            st.rerun()
        return True

    return True
