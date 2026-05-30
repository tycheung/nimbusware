from __future__ import annotations

import streamlit as st

from nimbusware_maker.api_client import get_json


def _status_color(status: str) -> str:
    return {
        "in_progress": "blue",
        "ready_for_next": "green",
        "complete": "green",
        "blocked": "red",
        "awaiting_plan": "orange",
    }.get(status, "gray")


def render_progress_panel(*, simple_mode: bool = True) -> None:
    st.subheader("Progress")
    run_id = st.text_input(
        "Run ID",
        value=st.session_state.get("maker_active_run_id", ""),
        key="maker_progress_run_id",
    )
    if not run_id.strip():
        st.info("Start a run from the Build tab, or paste a run ID here.")
        return

    st.session_state["maker_active_run_id"] = run_id.strip()
    try:
        path = f"/runs/{run_id.strip()}/maker-progress?simple={str(simple_mode).lower()}"
        progress = get_json(path)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load progress: {exc}")
        return

    headline = str(progress.get("current_headline") or "No progress yet")
    status = str(progress.get("status") or "unknown")
    st.markdown(f"### {headline}")
    st.caption(f"Status: :{_status_color(status)}[{status.replace('_', ' ')}]")

    plan_summary = str(progress.get("plan_summary") or "")
    if plan_summary:
        st.markdown(f"**Plan** — {plan_summary}")

    slice_index = progress.get("slice_index")
    slice_total = progress.get("slice_total")
    if isinstance(slice_index, int) and isinstance(slice_total, int):
        st.progress(min(max(slice_index / max(slice_total, 1), 0.0), 1.0))

    sentences = progress.get("sentences")
    if isinstance(sentences, list) and sentences:
        with st.expander("Timeline in plain language", expanded=True):
            for sentence in sentences:
                if isinstance(sentence, str) and sentence.strip():
                    st.markdown(f"- {sentence}")

    slices = progress.get("slices")
    if isinstance(slices, list):
        for item in slices:
            if not isinstance(item, dict):
                continue
            title = str(item.get("headline") or item.get("slice_id") or "Slice")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                rationale = str(item.get("rationale") or "").strip()
                if rationale:
                    st.caption(rationale)
                summary = item.get("test_summary")
                if isinstance(summary, dict):
                    bullets = summary.get("bullets")
                    if isinstance(bullets, list) and bullets:
                        st.markdown("**Tests**")
                        for bullet in bullets:
                            if isinstance(bullet, str):
                                st.markdown(f"- {bullet}")

    if not simple_mode:
        st.json(progress)
