from __future__ import annotations

import streamlit as st

from nimbusware_client.http import HTTPError
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403
from nimbusware_console.services import config_editors as cfg_svc


def render_workflows_bundle_editor_section() -> None:
    with st.expander("Bundle catalog editor (writes via API)", expanded=False):
        st.caption(
            "Edits use **PATCH /v1/bundles/catalog/bundles/{id}** (admin token). "
            "Reload catalog from API before saving."
        )
        _bc_admin = st.text_input(
            "X-Nimbusware-Admin-Token",
            key="hermes_bundle_edit_token",
            type="password",
        )
        if st.button("Reload bundle catalog from API", key="hermes_bundle_edit_reload"):
            try:
                st.session_state["hermes_bundle_edit_catalog"] = cfg_svc.load_bundle_catalog()
                st.success("Loaded bundle catalog from API.")
            except HTTPError as _bc_exc:
                render_api_error(_bc_exc)
        _bc_catalog = st.session_state.get("hermes_bundle_edit_catalog")
        if not isinstance(_bc_catalog, dict):
            st.caption("Click 'Reload bundle catalog from API' first.")
        else:
            _bc_bundles = _bc_catalog.get("bundles") or []
            _bc_ids = [
                str(b.get("id", "")) for b in _bc_bundles if isinstance(b, dict) and b.get("id")
            ]
            _bc_sel = st.selectbox(
                "Bundle",
                options=_bc_ids,
                key="hermes_bundle_edit_select",
            )
            _bc_row = next(
                (b for b in _bc_bundles if isinstance(b, dict) and str(b.get("id")) == _bc_sel),
                {},
            )
            st.text_input(
                "title",
                value=str(_bc_row.get("title") or ""),
                key="hermes_bundle_edit_title",
            )
            _bc_tags = _bc_row.get("tags") or []
            st.text_area(
                "tags (comma-separated)",
                value=", ".join(str(t) for t in _bc_tags if t is not None),
                key="hermes_bundle_edit_tags",
            )
            _bc_issues = bundle_editor_validation_issues(_bc_sel)
            if _bc_issues:
                for _msg in _bc_issues:
                    st.warning(_msg)
            if st.button(
                "Save bundle (PATCH)",
                key="hermes_bundle_edit_save",
                disabled=bool(_bc_issues) or not _bc_admin,
            ):
                _payload = bundle_editor_patch_payload(
                    title=str(st.session_state.get("hermes_bundle_edit_title", "")),
                    tags_text=str(st.session_state.get("hermes_bundle_edit_tags", "")),
                )
                try:
                    st.session_state["hermes_bundle_edit_catalog"] = cfg_svc.patch_bundle(
                        _bc_sel,
                        _payload,
                        _bc_admin,
                    )
                    st.success("Bundle catalog updated.")
                except HTTPError as _bc_patch_exc:
                    st.error(f"PATCH failed: {_bc_patch_exc}")
