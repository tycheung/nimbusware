from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import runs as runs_svc
from nimbusware_maker.ui.research_briefs import render_research_briefs_panel


def render_approval_panel() -> None:
    st.subheader("Review & apply")
    run_id = st.text_input(
        "Run ID",
        value=st.session_state.get("maker_active_run_id", ""),
        key="maker_approval_run_id",
    )
    if not run_id.strip():
        st.info("Start a run from the Build tab first.")
        return

    rid = run_id.strip()
    st.session_state["maker_active_run_id"] = rid
    render_research_briefs_panel(rid)
    st.divider()

    try:
        state = runs_svc.fetch_pending(rid)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load approval state: {exc}")
        return

    if not state.get("plan_approved"):
        st.markdown("**Step 1:** Approve the plan before any slice changes.")
        if st.button("Approve plan", type="primary"):
            try:
                runs_svc.approve_plan(rid)
                st.success("Plan approved.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not approve plan: {exc}")
        return

    pending = state.get("pending")
    if not pending:
        st.markdown("**Step 2:** Prepare the next slice for review.")
        if st.button("Prepare next slice"):
            try:
                body = runs_svc.prepare_slice(rid)
                if body.get("status") == "all_slices_done":
                    st.success("All planned slices are done.")
                else:
                    st.success("Slice ready for review.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not prepare slice: {exc}")
        if state.get("last_snapshot"):
            st.caption(f"Last snapshot: {state['last_snapshot'].get('snapshot_id')}")
            if st.button("Revert workspace to last approved snapshot"):
                try:
                    rev = runs_svc.revert_workspace(rid)
                    st.success(f"Reverted {len(rev.get('paths_restored', []))} file(s).")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Revert failed: {exc}")
        return

    slice_id = str(pending.get("slice_id") or "")
    st.markdown(f"**Pending slice:** `{slice_id}`")
    rationale = str(pending.get("rationale") or "").strip()
    if rationale:
        st.caption(rationale)

    diff = str(pending.get("diff_unified") or "")
    if diff:
        st.markdown("**Diff preview**")
        st.code(diff[:12000], language="diff")

    col_apply, col_skip, col_revert = st.columns(3)
    with col_apply:
        if st.button("Apply slice", type="primary"):
            try:
                result = runs_svc.apply_slice(rid, {"slice_id": slice_id})
                gate = "passed" if result.get("gate_passed") else "did not pass"
                st.success(f"Applied — gate {gate}.")
                commit = (
                    result.get("git_commit") if isinstance(result.get("git_commit"), dict) else {}
                )
                status = str(commit.get("status") or "")
                if status == "committed":
                    sha = str(commit.get("sha") or "")[:12]
                    branch = commit.get("branch") or ""
                    st.caption(f"Git commit: branch `{branch}`" + (f" @ `{sha}`" if sha else ""))
                elif status == "skipped":
                    st.caption(f"Git commit skipped: {commit.get('reason', 'disabled')}")
                elif status in ("failed", "error"):
                    st.caption(f"Git commit {status}: {commit.get('reason', '')}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Apply failed: {exc}")
    with col_skip:
        if st.button("Skip slice"):
            try:
                runs_svc.skip_slice(rid, {"slice_id": slice_id})
                st.success("Slice skipped.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Skip failed: {exc}")
    with col_revert:
        if st.button("Revert workspace"):
            try:
                rev = runs_svc.revert_workspace(rid)
                st.success(f"Reverted {len(rev.get('paths_restored', []))} file(s).")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Revert failed: {exc}")
