from __future__ import annotations

import streamlit as st

from nimbusware_client.http import admin_headers, get_json
from nimbusware_env.settings_catalog import SettingKind


def _admin_patch(path: str, payload: dict) -> dict:
    from nimbusware_client.http import request_response

    response = request_response(
        "PATCH",
        path,
        json=payload,
        headers=admin_headers(),
    )
    body = response.json()
    return body if isinstance(body, dict) else {}


def _render_field(item: dict, key_prefix: str) -> str | None:
    kind = str(item.get("kind") or "str")
    label = str(item.get("label") or item.get("key") or "")
    key = str(item.get("key") or "")
    desc = str(item.get("description") or "")
    current = item.get("value")
    default = str(item.get("default") or "")
    choices = item.get("choices") if isinstance(item.get("choices"), list) else []
    st.caption(desc)
    widget_key = f"{key_prefix}_{key}"
    if kind == SettingKind.BOOL.value:
        val = str(current or default) in ("1", "true", "yes", "on")
        checked = st.toggle(label, value=val, key=widget_key)
        return "1" if checked else "0"
    if kind == SettingKind.ENUM.value and choices:
        options = [str(c) for c in choices]
        idx = options.index(str(current)) if current in options else 0
        return st.selectbox(label, options, index=idx, key=widget_key)
    if kind == SettingKind.INT.value:
        try:
            num = int(str(current or default or "0"))
        except ValueError:
            num = 0
        return str(int(st.number_input(label, value=num, key=widget_key)))
    return st.text_input(label, value=str(current or default), key=widget_key)


def render_operator_settings_section() -> None:
    st.subheader("Operator settings (system)")
    st.caption("Admin-managed defaults in Postgres. Install/infra values remain in `.env`.")
    try:
        payload = get_json("/settings/system", headers=admin_headers())
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load system settings: {exc}")
        return

    groups = payload.get("groups") if isinstance(payload.get("groups"), dict) else {}
    patch: dict[str, str] = {}
    for group_name, items in groups.items():
        if not isinstance(items, list):
            continue
        with st.expander(group_name, expanded=False):
            for item in items:
                if not isinstance(item, dict) or not item.get("admin_editable", True):
                    continue
                val = _render_field(item, "admin_op")
                if val is not None and item.get("key"):
                    patch[str(item["key"])] = val

    if st.button("Save system settings", key="admin_op_save"):
        try:
            _admin_patch("/settings/system", {"values": patch})
            st.success("System settings saved.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    st.divider()
    st.markdown("**Install profile (read-only)**")
    try:
        install = get_json("/settings/install")
    except Exception as exc:  # noqa: BLE001
        st.caption(str(exc))
        return
    inst_groups = install.get("groups") if isinstance(install.get("groups"), dict) else {}
    for group_name, items in inst_groups.items():
        with st.expander(group_name, expanded=False):
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                st.text(f"{item.get('key')}: {item.get('value')}")
