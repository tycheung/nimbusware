from __future__ import annotations

import streamlit as st

from nimbusware_client.http import (
    HTTPError,
    Response,
    admin_token_headers,
    delete_response,
    patch_response,
    post_response,
    put_response,
)
from nimbusware_console.components.ui_errors import render_api_error
from nimbusware_console.pages.config_tooling.workflows._shared import *  # noqa: F403
from nimbusware_console.services import config_editors as cfg_svc


def render_workflows_persona_editor_section() -> None:
    with st.expander("Persona editor (writes via API)", expanded=False):
        st.caption(
            "Edits go through PATCH / PUT / POST / DELETE ``/v1/personas`` (writes "
            "shelves.yaml atomically; emits ``persona.shelf.updated`` audit event). "
            "Requires the ``X-Nimbusware-Admin-Token`` value below. "
            "Use 'Reload from API' to refresh the local snapshot before saving."
        )
        _admin_token = st.text_input(
            "X-Nimbusware-Admin-Token",
            key="hermes_persona_edit_token",
            type="password",
        )
        if st.button("Reload from API", key="hermes_persona_edit_reload_btn"):
            try:
                st.session_state["hermes_persona_edit_catalog"] = cfg_svc.load_persona_shelves()
                st.success("Loaded persona catalog from API.")
            except HTTPError as _exc:
                render_api_error(_exc)
        _editor_catalog = st.session_state.get("hermes_persona_edit_catalog")
        if not isinstance(_editor_catalog, dict):
            st.caption("Click 'Reload from API' to load the catalog before editing.")
        else:
            _shelf = st.selectbox(
                "Shelf",
                options=["business_area", "development_role"],
                key="hermes_persona_edit_shelf",
            )
            _shelf_cap = persona_editor_selected_shelf_caption(_shelf)
            if _shelf_cap:
                st.caption(_shelf_cap)
            _ids = [
                str(e.get("id", ""))
                for e in (_editor_catalog.get(_shelf) or [])
                if isinstance(e, dict) and e.get("id")
            ]
            _selected = st.selectbox(
                "Persona (existing) — or pick '(new)' to create a new entry",
                options=["(new)", *_ids],
                key="hermes_persona_edit_select",
            )
            _existing = (
                find_persona_in_catalog(_editor_catalog, _shelf, _selected)
                if _selected != "(new)"
                else None
            )
            _snapshot: dict[str, Any] = dict(_existing) if _existing else {}
            st.text_input(
                "id",
                value=str(_snapshot.get("id", "")),
                key="hermes_persona_edit_id",
                disabled=_existing is not None,
                help="Cannot be changed after creation; use DELETE + POST to rename.",
            )
            st.text_input(
                "display_name",
                value=str(_snapshot.get("display_name", "")),
                key="hermes_persona_edit_display_name",
            )
            _dn_cap = persona_editor_display_name_draft_caption(
                st.session_state.get("hermes_persona_edit_display_name", ""),
            )
            if _dn_cap:
                st.caption(_dn_cap)
            st.text_area(
                "instructions (system prompt; up to 8000 chars)",
                value=str(_snapshot.get("instructions", "")),
                key="hermes_persona_edit_instructions",
                height=200,
            )
            _ins_cap = persona_editor_instructions_metrics_caption(
                st.session_state.get("hermes_persona_edit_instructions", ""),
            )
            if _ins_cap:
                st.caption(_ins_cap)
            st.text_area(
                "capability_profile (up to 2000 chars)",
                value=str(_snapshot.get("capability_profile", "")),
                key="hermes_persona_edit_capability_profile",
                height=120,
            )
            st.text_area(
                "boundary_statement (up to 2000 chars)",
                value=str(_snapshot.get("boundary_statement", "")),
                key="hermes_persona_edit_boundary_statement",
                height=120,
            )
            _multi_cap = persona_editor_multiline_field_metrics_caption(
                st.session_state.get("hermes_persona_edit_capability_profile", ""),
                st.session_state.get("hermes_persona_edit_boundary_statement", ""),
            )
            if _multi_cap:
                st.caption(_multi_cap)
            st.text_area(
                "allowed_tools (one per line, up to 50)",
                value="\n".join(_snapshot.get("allowed_tools") or []),
                key="hermes_persona_edit_allowed_tools",
                height=100,
            )
            st.text_area(
                "success_metrics (one per line, up to 20)",
                value="\n".join(_snapshot.get("success_metrics") or []),
                key="hermes_persona_edit_success_metrics",
                height=100,
            )
            _list_fields_cap = persona_list_field_line_counts_caption(
                st.session_state.get("hermes_persona_edit_allowed_tools", ""),
                st.session_state.get("hermes_persona_edit_success_metrics", ""),
            )
            if _list_fields_cap:
                st.caption(_list_fields_cap)
            st.selectbox(
                "probation_status",
                options=["promoted", "probation", "shelved"],
                index=["promoted", "probation", "shelved"].index(
                    str(_snapshot.get("probation_status") or "promoted"),
                ),
                key="hermes_persona_edit_probation_status",
            )
            _prob_draft_cap = persona_editor_probation_status_draft_caption(
                st.session_state.get("hermes_persona_edit_probation_status"),
            )
            if _prob_draft_cap:
                st.caption(_prob_draft_cap)
            st.text_input(
                "actor (optional; recorded in the audit event)",
                key="hermes_persona_edit_actor",
            )

            def _split_lines(raw: str) -> list[str]:
                return [ln.strip() for ln in raw.splitlines() if ln.strip()]

            _edited: dict[str, Any] = {
                "id": st.session_state["hermes_persona_edit_id"].strip(),
                "display_name": st.session_state["hermes_persona_edit_display_name"].strip()
                or None,
                "instructions": st.session_state["hermes_persona_edit_instructions"] or None,
                "capability_profile": st.session_state["hermes_persona_edit_capability_profile"]
                or None,
                "boundary_statement": st.session_state["hermes_persona_edit_boundary_statement"]
                or None,
                "allowed_tools": _split_lines(
                    st.session_state["hermes_persona_edit_allowed_tools"],
                )
                or None,
                "success_metrics": _split_lines(
                    st.session_state["hermes_persona_edit_success_metrics"],
                )
                or None,
                "probation_status": st.session_state["hermes_persona_edit_probation_status"],
            }
            _diff = diff_summary(_snapshot, _edited) if _existing else []
            if _existing:
                _prob_cap = persona_editor_probation_status_caption(_snapshot)
                if _prob_cap:
                    st.caption(_prob_cap)
                _ver_cap = persona_editor_expected_version_caption(_snapshot)
                if _ver_cap:
                    st.caption(_ver_cap)
                _diff_cap = persona_editor_diff_summary_caption(_snapshot, _edited)
                if _diff_cap:
                    st.caption(_diff_cap)
            if _diff:
                with st.expander("Diff preview", expanded=False):
                    for line in _diff:
                        st.write(f"- {line}")

            _validation_issues = persona_editor_validation_issues(
                _edited,
                require_non_empty_id=_existing is None,
            )
            _validation_cap = persona_editor_validation_blocking_caption(
                _validation_issues,
            )
            if _validation_cap:
                st.caption(_validation_cap)
            _validation_rows = persona_editor_validation_table_rows(_validation_issues)
            if _validation_rows:
                st.dataframe(_validation_rows, use_container_width=True)
            _write_blocked = bool(_validation_issues)

            _actor = st.session_state["hermes_persona_edit_actor"].strip() or None
            _headers = admin_token_headers(_admin_token)
            _col_save, _col_replace, _col_delete, _col_create = st.columns(4)

            def _handle_write_response(label: str, r: Response) -> None:
                try:
                    body = r.json() if r.content else None
                except json.JSONDecodeError:
                    body = None
                parsed = parse_write_response(r.status_code, body)
                if parsed["ok"]:
                    st.session_state["hermes_persona_edit_catalog"] = parsed["catalog"]
                    st.success(f"{label}: 2xx (catalog refreshed).")
                elif parsed.get("version_conflict"):
                    st.warning(f"{label}: 409 version conflict — reload from API and retry.")
                else:
                    st.error(f"{label}: {parsed['status']} {parsed['code']} — {parsed['message']}")

            with _col_save:
                if st.button(
                    "Save (PATCH)",
                    key="hermes_persona_edit_save_btn",
                    disabled=_existing is None or _write_blocked,
                ):
                    req = build_patch_request(_snapshot, _edited, actor=_actor)
                    try:
                        _resp = patch_response(
                            f"/personas/{_shelf}/{_selected}",
                            req,
                            headers=_headers,
                            timeout=10.0,
                            raise_for_status=False,
                        )
                        _handle_write_response("PATCH", _resp)
                    except HTTPError as _exc:
                        render_api_error(_exc)
            with _col_replace:
                if st.button(
                    "Replace (PUT)",
                    key="hermes_persona_edit_replace_btn",
                    disabled=_existing is None or _write_blocked,
                ):
                    entry_body = {k: v for k, v in _edited.items() if v is not None}
                    entry_body["id"] = _snapshot.get("id", _selected)
                    put_body = {
                        "entry": entry_body,
                        "expected_version": int(_snapshot.get("version", 1) or 1),
                        "actor": _actor,
                    }
                    try:
                        _resp = put_response(
                            f"/personas/{_shelf}/{_selected}",
                            put_body,
                            headers=_headers,
                            timeout=10.0,
                            raise_for_status=False,
                        )
                        _handle_write_response("PUT", _resp)
                    except HTTPError as _exc:
                        render_api_error(_exc)
            with _col_delete:
                if st.button(
                    "Delete",
                    key="hermes_persona_edit_delete_btn",
                    disabled=_existing is None,
                ):
                    try:
                        _resp = delete_response(
                            f"/personas/{_shelf}/{_selected}",
                            params={
                                "expected_version": int(
                                    _snapshot.get("version", 1) or 1,
                                ),
                                **({"actor": _actor} if _actor else {}),
                            },
                            headers=_headers,
                            timeout=10.0,
                            raise_for_status=False,
                        )
                        _handle_write_response("DELETE", _resp)
                    except HTTPError as _exc:
                        render_api_error(_exc)
            with _col_create:
                if st.button(
                    "Create (POST)",
                    key="hermes_persona_edit_create_btn",
                    disabled=_existing is not None or _write_blocked,
                ):
                    new_id = st.session_state["hermes_persona_edit_id"].strip()
                    if not new_id:
                        st.error("Set a non-empty id before creating.")
                    elif _write_blocked:
                        pass
                    else:
                        entry_body = {k: v for k, v in _edited.items() if v is not None}
                        entry_body["id"] = new_id
                        post_body = {"entry": entry_body, "actor": _actor}
                        try:
                            _resp = post_response(
                                f"/personas/{_shelf}",
                                payload=post_body,
                                headers=_headers,
                                timeout=10.0,
                                raise_for_status=False,
                            )
                            _handle_write_response("POST", _resp)
                        except HTTPError as _exc:
                            render_api_error(_exc)
