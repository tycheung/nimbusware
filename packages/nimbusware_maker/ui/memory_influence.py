"""Maker panel: memory chunks that influenced a slice."""

from __future__ import annotations

from typing import Any

import streamlit as st

from hermes_memory.timeline import memory_retrieval_entries_for_slice


def format_retrieval_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Normalize retrieval rows for display (testable without Streamlit)."""
    out: list[dict[str, str]] = []
    for row in rows:
        hits = row.get("hit_chunk_ids") or []
        hit_preview = ", ".join(str(h)[:12] for h in hits[:5])
        if len(hits) > 5:
            hit_preview += f" (+{len(hits) - 5} more)"
        digest = str(row.get("query_digest") or "")
        out.append(
            {
                "stage": str(row.get("stage_name") or ""),
                "hits": str(row.get("hit_count") or 0),
                "excerpt_chars": str(row.get("excerpt_chars") or 0),
                "query_digest": digest[:16] + "…" if len(digest) > 16 else digest,
                "chunk_ids": hit_preview or "—",
                "occurred_at": str(row.get("occurred_at") or ""),
            },
        )
    return out


def render_memory_influence_panel(*, events: list[dict[str, Any]] | None = None) -> None:
    st.subheader("Memory influence")
    st.caption("Shows `memory.retrieval.emitted` events for the selected slice.")

    run_id = st.text_input(
        "Run ID",
        value=st.session_state.get("maker_active_run_id", ""),
        key="maker_memory_influence_run_id",
    ).strip()
    slice_id = st.text_input("Slice ID", key="maker_memory_influence_slice_id").strip()

    if events is None:
        if not run_id:
            st.info("Enter a run ID to load memory retrievals.")
            return
        try:
            from nimbusware_maker.services import runs as runs_svc

            body = runs_svc.fetch_run_timeline(run_id)
            raw = body.get("events") if isinstance(body, dict) else None
            events = list(raw) if isinstance(raw, list) else []
        except Exception as exc:
            st.error(f"Could not load run events: {exc}")
            return

    if not slice_id:
        st.info("Enter a slice ID to filter retrievals.")
        return

    rows = memory_retrieval_entries_for_slice(events, slice_id)
    if not rows:
        st.warning("No memory retrievals recorded for this slice yet.")
        return

    st.dataframe(format_retrieval_rows(rows), use_container_width=True, hide_index=True)
