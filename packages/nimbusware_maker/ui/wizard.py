from __future__ import annotations

import streamlit as st

from nimbusware_maker.intent import CLARIFYING_QUESTIONS
from nimbusware_maker.onboarding import SESSION_WIZARD_STEP, is_onboarded, mark_onboarded
from nimbusware_maker.readiness_smoke import readiness_smoke_ok
from nimbusware_maker.services import hardware as hw_svc
from nimbusware_maker.services import operator_settings as settings_svc
from nimbusware_maker.services import platform as platform_svc
from nimbusware_maker.services import projects as projects_svc
from nimbusware_maker.services import runs as runs_svc
from nimbusware_maker.wizard_model import (
    fit_level_caption,
    model_options_for_select,
    pick_recommended_model,
)

_WIZARD_STEPS = 5


def render_first_run_wizard() -> bool:
    if is_onboarded(st.session_state):
        return False

    st.subheader("Welcome to Nimbusware Maker")
    st.markdown(
        "This setup picks a project folder, checks readiness, chooses a model, "
        "and starts your first small iteration.",
    )

    step = int(st.session_state.get(SESSION_WIZARD_STEP, 1))
    st.progress(step / float(_WIZARD_STEPS))

    if step == 1:
        st.markdown(f"**Step 1 of {_WIZARD_STEPS} — Project folder**")
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
        st.markdown(f"**Step 2 of {_WIZARD_STEPS} — Local readiness**")
        try:
            readiness = platform_svc.fetch_readiness()
            status = str(readiness.get("status") or "unknown")
            st.info(f"Platform status: {status.replace('_', ' ')}")
            checks = readiness.get("checks")
            if isinstance(checks, dict):
                for name, check in checks.items():
                    if isinstance(check, dict):
                        st.caption(f"{name}: {check.get('message', '')}")
            ollama = checks.get("ollama") if isinstance(checks, dict) else None
            if isinstance(ollama, dict):
                pull = ollama.get("pull_command")
                if isinstance(pull, str) and pull.strip():
                    st.session_state["wizard_ollama_pull"] = pull.strip()
                    st.markdown("If Ollama is running but the model is missing:")
                    st.code(pull.strip())
            guide = readiness.get("install_guide")
            if isinstance(guide, str) and guide.strip():
                st.caption(f"Setup: {guide}")
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
                try:
                    readiness = platform_svc.fetch_readiness()
                except Exception as exc:  # noqa: BLE001
                    st.error(
                        f"Cannot reach the API ({exc}). Start it with: poetry run nimbusware-api",
                    )
                else:
                    ok, msg = readiness_smoke_ok(readiness)
                    if not ok:
                        st.error(msg)
                    else:
                        st.session_state[SESSION_WIZARD_STEP] = 3
                        st.rerun()
        return True

    if step == 3:
        st.markdown(f"**Step 3 of {_WIZARD_STEPS} — Choose a model**")
        ranked: list = []
        profile: dict = {}
        try:
            hw = hw_svc.fetch_hardware()
            profile = hw.get("profile") if isinstance(hw.get("profile"), dict) else {}
            ranked = hw.get("models_ranked") if isinstance(hw.get("models_ranked"), list) else []
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not load hardware profile: {exc}")
        tier = str(profile.get("tier") or "unknown")
        st.caption(f"Hardware tier: **{tier}**")
        ram = profile.get("ram_available_gb")
        if ram is not None:
            st.caption(f"Available RAM: {ram} GB")
        if st.button("Rescan hardware", key="wizard_hw_rescan"):
            try:
                hw_svc.rescan_hardware()
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        options = model_options_for_select(ranked)
        default_id = pick_recommended_model(ranked) or (options[0][1] if options else "")
        if options:
            labels = [o[0] for o in options]
            idx = next((i for i, o in enumerate(options) if o[1] == default_id), 0)
            choice_label = st.selectbox("Recommended model for this machine", labels, index=idx)
            model_id = options[labels.index(choice_label)][1]
            for row in ranked:
                if row.get("model_id") == model_id:
                    st.caption(fit_level_caption(str(row.get("fit_level", ""))))
                    break
            st.session_state["wizard_model_id"] = model_id
        else:
            st.caption("No ranked models yet — check Settings → Hardware after setup.")
        pull = st.session_state.get("wizard_ollama_pull")
        if isinstance(pull, str) and pull.strip():
            st.code(pull.strip())
        cols = st.columns(2)
        with cols[0]:
            if st.button("Back"):
                st.session_state[SESSION_WIZARD_STEP] = 2
                st.rerun()
        with cols[1]:
            if st.button("Next", type="primary"):
                mid = st.session_state.get("wizard_model_id")
                if mid:
                    try:
                        settings_svc.patch_user_settings(
                            {"NIMBUSWARE_PREFERRED_MODEL_ID": str(mid)},
                        )
                        from nimbusware_maker.services import models as models_svc

                        models_svc.apply_model_preset(model_id=str(mid), preset="balanced")
                    except Exception:
                        pass
                st.session_state[SESSION_WIZARD_STEP] = 4
                st.rerun()
        return True

    if step == 4:
        st.markdown(f"**Step 4 of {_WIZARD_STEPS} — What do you want to build?**")
        business_prompt = st.text_area(
            "Business prompt",
            placeholder="A simple inventory tracker for my shop…",
            height=100,
        )
        st.session_state["wizard_business_prompt"] = business_prompt
        clarifications: list[dict[str, str]] = []
        st.markdown("**A few clarifying questions (optional)**")
        for item in CLARIFYING_QUESTIONS:
            answer = st.text_input(
                item["question"],
                key=f"wizard_clarify_{item['id']}",
            )
            if answer.strip():
                clarifications.append(
                    {
                        "question_id": item["id"],
                        "question": item["question"],
                        "answer": answer.strip(),
                    },
                )
        st.session_state["wizard_clarifications"] = clarifications
        cols = st.columns(2)
        with cols[0]:
            if st.button("Back"):
                st.session_state[SESSION_WIZARD_STEP] = 3
                st.rerun()
        with cols[1]:
            if st.button("Next", type="primary"):
                if not business_prompt.strip():
                    st.error("Describe what you want to build.")
                else:
                    st.session_state[SESSION_WIZARD_STEP] = 5
                    st.rerun()
        return True

    if step == 5:
        st.markdown(f"**Step {_WIZARD_STEPS} of {_WIZARD_STEPS} — Create project and start**")
        project_cfg = st.session_state.get("wizard_project") or {}
        prompt = str(st.session_state.get("wizard_business_prompt") or "").strip()
        clarifications = st.session_state.get("wizard_clarifications")
        if not isinstance(clarifications, list):
            clarifications = []
        model_id = st.session_state.get("wizard_model_id")
        if model_id:
            st.caption(f"Selected model: `{model_id}`")
        if st.button("Finish setup", type="primary"):
            try:
                project = projects_svc.create_project(
                    {
                        "name": project_cfg.get("name", "My app"),
                        "workspace_path": project_cfg.get("workspace_path", "."),
                        "template": project_cfg.get("template", "greenfield"),
                        "default_workflow_profile": "micro_slice",
                    },
                )
                req: dict = {
                    "business_prompt": prompt,
                    "clarifications": clarifications,
                }
                if model_id:
                    req["preferred_model_id"] = str(model_id)
                run = runs_svc.create_run(
                    {
                        "workflow_profile": "micro_slice",
                        "project_id": project.get("project_id"),
                        "requirements": req,
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
            st.session_state[SESSION_WIZARD_STEP] = 4
            st.rerun()
        return True

    return True
