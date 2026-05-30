from __future__ import annotations

import streamlit as st

from nimbusware_maker.api_client import get_json, post_json


from nimbusware_maker.runs import latest_run_id_for_project


def _status_emoji(status: str) -> str:
    return {"ready": "🟢", "degraded": "🟡", "not_ready": "🔴"}.get(status, "⚪")


def render_readiness_strip() -> dict:
    try:
        readiness = get_json("/platform/readiness")
    except Exception as exc:  # noqa: BLE001 — show plain-language error in UI
        st.error(f"Could not reach the API readiness endpoint: {exc}")
        return {}

    overall = str(readiness.get("status") or "unknown")
    st.subheader(f"{_status_emoji(overall)} Local readiness — {overall.replace('_', ' ')}")
    checks = readiness.get("checks")
    if isinstance(checks, dict):
        cols = st.columns(len(checks))
        for col, (name, check) in zip(cols, checks.items(), strict=False):
            if not isinstance(check, dict):
                continue
            status = str(check.get("status") or "unknown")
            col.metric(
                label=name.replace("_", " ").title(),
                value=status,
                help=str(check.get("message") or ""),
            )
    presets = readiness.get("presets")
    if isinstance(presets, dict):
        with st.expander("Model presets"):
            for key, preset in presets.items():
                if isinstance(preset, dict):
                    st.markdown(
                        f"**{preset.get('label', key)}** — {preset.get('hint', '')}",
                    )
    if overall == "not_ready":
        guide = readiness.get("install_guide")
        if isinstance(guide, str) and guide.strip():
            st.warning(f"Setup help: `{guide}`")
    return readiness


def render_projects_panel() -> None:
    st.subheader("Projects")
    try:
        listing = get_json("/projects")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Projects API unavailable: {exc}")
        return

    projects = listing.get("projects")
    if not isinstance(projects, list) or not projects:
        st.info("No projects yet. Create one below to bind runs to your workspace folder.")
    else:
        for project in projects:
            if not isinstance(project, dict):
                continue
            st.markdown(
                f"**{project.get('name', 'Project')}** — `{project.get('workspace_path', '')}`",
            )
            pid = str(project.get("project_id") or "")
            cols = st.columns(2)
            with cols[0]:
                if st.button("Use for build", key=f"use-{pid}"):
                    st.session_state["maker_active_project_id"] = pid
                    st.info("Switch to the Build tab to describe your intent and start a run.")
            with cols[1]:
                if pid and st.button("Continue last run", key=f"continue-{pid}"):
                    try:
                        run_id = latest_run_id_for_project(pid)
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not load runs: {exc}")
                    else:
                        if run_id:
                            st.session_state["maker_active_project_id"] = pid
                            st.session_state["maker_active_run_id"] = run_id
                            st.success(f"Resumed run {run_id} — open Review or Progress.")
                        else:
                            st.info("No runs yet for this project. Use Build to start one.")

    with st.form("create_project"):
        st.markdown("**New project**")
        name = st.text_input("Name", placeholder="My app")
        workspace_path = st.text_input(
            "Workspace folder",
            placeholder="C:/Users/you/projects/my-app",
        )
        template = st.selectbox("Template", ["attach", "greenfield"])
        profile = st.text_input("Default workflow profile", value="micro_slice")
        submitted = st.form_submit_button("Create project")
        if submitted:
            try:
                created = post_json(
                    "/projects",
                    {
                        "name": name,
                        "workspace_path": workspace_path,
                        "template": template,
                        "default_workflow_profile": profile,
                    },
                )
                st.success(f"Created project {created.get('name')}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not create project: {exc}")
