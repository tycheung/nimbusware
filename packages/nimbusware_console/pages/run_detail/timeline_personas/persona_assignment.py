from __future__ import annotations

import os
from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports_common import (
    datetime,
    os,
    st,
    timezone,
)
from nimbusware_console.pages.run_detail._imports_display_a import (
    persona_assignment_caption,
    persona_assignment_from_timeline,
    persona_assignment_summary_rows,
    persona_assignment_timeline_export_json,
    persona_assignment_timeline_table_rows_csv,
)


def _workflow_profile_pick(data: dict[str, Any]) -> str:
    wf = data.get("workflow_profile") if isinstance(data, dict) else None
    if isinstance(wf, str) and wf.strip():
        return wf.strip()
    from nimbusware_env.env_flags import nimbusware_workflow_profile

    return nimbusware_workflow_profile()


def _run_slug(run_id: str, *, max_len: int = 36) -> str:
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_id.strip())
    return (slug or "run")[:max_len]


def _workflow_profile_pick(data: dict[str, Any]) -> str:
    wf = data.get("workflow_profile") if isinstance(data, dict) else None
    if isinstance(wf, str) and wf.strip():
        return wf.strip()
    from nimbusware_env.env_flags import nimbusware_workflow_profile

    return nimbusware_workflow_profile()


def _run_slug(run_id: str, *, max_len: int = 36) -> str:
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_id.strip())
    return (slug or "run")[:max_len]


def _render_persona_assignment(run_id: str, data: dict) -> None:
    _ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    _slug = _run_slug(run_id.strip())

    _pa = persona_assignment_from_timeline(data)
    _pa_rows = persona_assignment_summary_rows(_pa)
    with st.expander("Persona assignment (from timeline)", expanded=False):
        if not _pa_rows:
            st.caption(
                "No persona_assignment on this timeline (create_run did not "
                "set business_area_persona_id / development_role_persona_id)."
            )
        else:
            st.caption(
                "Frozen composite persona from the first run.created "
                "(same top-level persona_assignment as GET …/timeline)."
            )
            _pa_cap = persona_assignment_caption(_pa)
            if _pa_cap:
                st.caption(_pa_cap)
            st.dataframe(_pa_rows, use_container_width=True)
            _pa_csv = persona_assignment_timeline_table_rows_csv(_pa_rows)
            _pa_json = persona_assignment_timeline_export_json(_pa)
            _pa_dl_col, _pa_dl_json_col = st.columns(2)
            with _pa_dl_col:
                st.download_button(
                    label="Download persona assignment CSV",
                    data=_pa_csv.encode("utf-8"),
                    file_name=f"hermes_persona_assignment_{_slug}_{_ts}.csv",
                    mime="text/csv; charset=utf-8",
                    key="hermes_dl_persona_assignment_csv",
                )
            with _pa_dl_json_col:
                st.download_button(
                    label="Download persona assignment JSON",
                    data=_pa_json.encode("utf-8"),
                    file_name=f"hermes_persona_assignment_{_slug}_{_ts}.json",
                    mime="application/json",
                    key="hermes_dl_persona_assignment_json",
                )
            with st.expander("Raw persona_assignment JSON", expanded=False):
                st.json(_pa)
