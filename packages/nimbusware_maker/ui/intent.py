from __future__ import annotations

import streamlit as st

from nimbusware_maker.intent import CLARIFYING_QUESTIONS
from nimbusware_maker.services import projects as projects_svc
from nimbusware_maker.services import runs as runs_svc


def _project_options(projects: list[dict]) -> dict[str, str]:
    return {
        str(p.get("project_id")): str(p.get("name") or p.get("project_id"))
        for p in projects
        if isinstance(p, dict) and p.get("project_id")
    }


def render_intent_wizard() -> None:
    st.subheader("Describe what you want")
    try:
        listing = projects_svc.list_projects()
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Projects API unavailable: {exc}")
        return

    projects = listing.get("projects")
    if not isinstance(projects, list) or not projects:
        st.info("Create a project on the Home tab before starting a maker run.")
        return

    options = _project_options(projects)
    default_project = st.session_state.get("maker_active_project_id")
    if default_project not in options:
        default_project = next(iter(options))

    project_id = st.selectbox(
        "Project",
        options=list(options.keys()),
        format_func=lambda pid: options.get(str(pid), pid),
        index=list(options.keys()).index(default_project)
        if default_project in options
        else 0,
        key="maker_intent_project",
    )
    st.session_state["maker_active_project_id"] = project_id
    project = next(p for p in projects if str(p.get("project_id")) == str(project_id))

    business_prompt = st.text_area(
        "Business prompt",
        placeholder="I need a small inventory tracker for my shop…",
        height=120,
        key="maker_business_prompt",
    )

    st.markdown("**A few clarifying questions**")
    clarifications: list[dict[str, str]] = []
    for item in CLARIFYING_QUESTIONS:
        answer = st.text_input(
            item["question"],
            key=f"maker_clarify_{item['id']}",
        )
        if answer.strip():
            clarifications.append(
                {
                    "question_id": item["id"],
                    "question": item["question"],
                    "answer": answer.strip(),
                },
            )

    if st.button("Start run with this intent", type="primary"):
        if not business_prompt.strip():
            st.error("Enter a business prompt first.")
            return
        try:
            run = runs_svc.create_run(
                {
                    "workflow_profile": project.get("default_workflow_profile", "micro_slice"),
                    "project_id": project_id,
                    "requirements": {
                        "business_prompt": business_prompt.strip(),
                        "clarifications": clarifications,
                    },
                },
            )
            run_id = str(run.get("run_id") or "")
            st.session_state["maker_active_run_id"] = run_id
            st.success(f"Run started — {run_id}")
            st.info("Open the Review tab to approve the plan, then apply each slice.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not start run: {exc}")
