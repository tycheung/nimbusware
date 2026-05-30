from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import Path, os, st
from nimbusware_console.pages.run_detail._imports_display_b import (
    latest_slice_context_packet_from_timeline,
    memory_indexed_timeline_summary,
    memory_retrieval_timeline_summary,
    phase3_critique_caption,
    phase3_critique_table_rows,
)


def _render_timeline_misc_core(run_id: str, data: dict, _wf_pick: str) -> None:
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    _wf_pick = data.get("workflow_profile") if isinstance(data, dict) else None
    if not isinstance(_wf_pick, str) or not _wf_pick.strip():
        _wf_pick = os.environ.get("HERMES_WORKFLOW_PROFILE", "nimbusware_production")
    with st.expander("Phase 3 critic stages (from timeline)", expanded=False):
        st.caption(phase3_critique_caption(data))
        _p3_rows = phase3_critique_table_rows(data)
        if _p3_rows:
            st.dataframe(_p3_rows, use_container_width=True)
    _ms_tl = data.get("micro_slice") if isinstance(data, dict) else None
    if isinstance(_ms_tl, dict) and _ms_tl:
        with st.expander("Micro-slice summary (from timeline)", expanded=False):
            st.json(_ms_tl)
        _pkt = latest_slice_context_packet_from_timeline(data)
        if _pkt:
            with st.expander("Slice context packet (latest)", expanded=False):
                st.json(_pkt)
    _mem_ret = memory_retrieval_timeline_summary(data.get("events") or [])
    _mem_idx = memory_indexed_timeline_summary(data.get("events") or [])
    if _mem_ret or _mem_idx:
        with st.expander("Memory retrieval / index (from timeline)", expanded=False):
            if _mem_ret:
                st.caption("Last retrieval event summary")
                st.json(_mem_ret)
            if _mem_idx:
                st.caption("Last memory.indexed summary")
                st.json(_mem_idx)
