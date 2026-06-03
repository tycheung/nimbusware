from __future__ import annotations

import streamlit as st

from nimbusware_maker.runs import list_runs_for_project
from nimbusware_maker.services import platform as platform_svc
from nimbusware_maker.services import projects as projects_svc


def _status_emoji(status: str) -> str:
    return {"ready": "🟢", "degraded": "🟡", "not_ready": "🔴"}.get(status, "⚪")


def render_readiness_strip() -> dict:
    try:
        readiness = platform_svc.fetch_readiness()
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
    try:
        from nimbusware_maker.services import hardware as hw_svc

        hw = hw_svc.fetch_hardware()
        profile = hw.get("profile") if isinstance(hw.get("profile"), dict) else {}
        tier = str(profile.get("tier") or "")
        ranked = hw.get("models_ranked") if isinstance(hw.get("models_ranked"), list) else []
        if tier == "weak" or (
            ranked and all(r.get("fit_level") == "too_tight" for r in ranked if isinstance(r, dict))
        ):
            st.caption(
                "Hardware tier is limited — open **Settings → Hardware** "
                "or rerun setup to pick a smaller model.",
            )
    except Exception:
        pass
    return readiness


def render_projects_panel() -> None:
    st.subheader("Projects")
    try:
        listing = projects_svc.list_projects()
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
                        runs = list_runs_for_project(pid)
                        run_id = runs[0]["run_id"] if runs else None
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not load runs: {exc}")
                    else:
                        if run_id:
                            st.session_state["maker_active_project_id"] = pid
                            st.session_state["maker_active_run_id"] = run_id
                            st.success(f"Resumed run {run_id} — open Review or Progress.")
                        else:
                            st.info("No runs yet for this project. Use Build to start one.")
            history = []
            if pid:
                try:
                    history = list_runs_for_project(pid, limit=10)
                except Exception:
                    history = []
            if history:
                with st.expander("Run history", expanded=False):
                    for row in history:
                        rid = row.get("run_id", "")
                        status = row.get("status", "unknown")
                        cols_h = st.columns([3, 1])
                        cols_h[0].markdown(f"`{rid}` — {status}")
                        if cols_h[1].button("Open", key=f"hist-{pid}-{rid}"):
                            st.session_state["maker_active_project_id"] = pid
                            st.session_state["maker_active_run_id"] = rid
                            st.info("Switch to Review or Progress for this run.")

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
                created = projects_svc.create_project(
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
