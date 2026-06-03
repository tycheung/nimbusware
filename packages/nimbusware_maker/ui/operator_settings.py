from __future__ import annotations

import streamlit as st

from nimbusware_env.settings_catalog import SettingKind
from nimbusware_maker.services import operator_settings as settings_svc


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
        val = bool(str(current or default) in ("1", "true", "yes", "on"))
        if not current and default in ("1", "true", "yes"):
            val = True
        checked = st.toggle(label, value=val, key=widget_key)
        return "1" if checked else "0"
    if kind == SettingKind.ENUM.value and choices:
        options = [str(c) for c in choices]
        idx = options.index(str(current)) if current in options else 0
        picked = st.selectbox(label, options, index=idx, key=widget_key)
        return picked
    if kind == SettingKind.INT.value:
        try:
            num = int(str(current or default or "0"))
        except ValueError:
            num = 0
        picked = st.number_input(label, value=num, key=widget_key)
        return str(int(picked))
    text = st.text_input(label, value=str(current or default), key=widget_key)
    return text


def render_operator_settings_panel() -> None:
    st.markdown("**Operator settings**")
    st.caption(
        "Maker preferences stored in Postgres (user profile). "
        "Install secrets stay in `.env`; system defaults are in Admin Console."
    )
    try:
        payload = settings_svc.fetch_user_settings()
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load settings: {exc}")
        return

    groups = payload.get("groups") if isinstance(payload.get("groups"), dict) else {}
    if not groups:
        st.info("No user-scoped settings in catalog.")
        return

    patch: dict[str, str] = {}
    _expanded_groups = frozenset(
        {
            "User — git outputs",
            "User — maker runtime",
            "User — hardware governor",
        },
    )
    for group_name, items in groups.items():
        if not isinstance(items, list):
            continue
        expanded = group_name in _expanded_groups
        with st.expander(group_name, expanded=expanded):
            if group_name == "User — git outputs":
                st.caption("Native git output paths and branch prefix for slice commits.")
            for item in items:
                if not isinstance(item, dict) or not item.get("user_editable", True):
                    continue
                val = _render_field(item, "maker_op")
                if val is not None and item.get("key"):
                    patch[str(item["key"])] = val

    if st.button("Save operator settings", key="maker_op_save"):
        try:
            settings_svc.patch_user_settings(patch)
            st.success("Saved. API workers reload values on next request.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
