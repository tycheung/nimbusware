from __future__ import annotations

import streamlit as st

from nimbusware_maker.services import ollama as ollama_svc


def _format_size(size_bytes: object) -> str:
    if not isinstance(size_bytes, int) or size_bytes < 0:
        return "—"
    if size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.1f} MB"
    return f"{size_bytes / 1024**3:.2f} GB"


def render_ollama_models_panel() -> None:
    st.markdown("**Ollama models**")
    st.caption("Local models from your Ollama runtime. Some actions require admin-enabled policy.")

    query = st.text_input(
        "Search models",
        key="maker_ollama_query",
        placeholder="Filter by name",
    )

    try:
        data = ollama_svc.list_models(query=query)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Could not load Ollama models: {exc}")
        return

    policy = data.get("user_policy") if isinstance(data.get("user_policy"), dict) else {}
    allow_pull = bool(policy.get("allow_pull"))
    allow_delete = bool(policy.get("allow_delete"))
    allow_routing = bool(policy.get("allow_update_routing"))

    reachable = bool(data.get("reachable"))
    primary = data.get("primary_model_id")
    st.caption(
        f"Runtime `{data.get('base_url', '')}` · reachable: **{'yes' if reachable else 'no'}** · "
        f"primary: `{primary or '—'}`",
    )

    if not reachable:
        st.info("Start Ollama locally or fix `configs/model-routing.yaml` runtime.base_url.")

    if allow_pull:
        pull_name = st.text_input("Pull model", key="maker_ollama_pull", placeholder="model:tag")
        if st.button("Pull", key="maker_ollama_pull_btn") and pull_name.strip():
            try:
                ollama_svc.pull_model(pull_name.strip())
                st.success(f"Pulled {pull_name.strip()}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
    else:
        st.caption("Pull is disabled — ask an admin to enable **Users may pull models**.")

    if allow_routing and primary:
        options = [
            str(m.get("name"))
            for m in (data.get("models") or [])
            if isinstance(m, dict) and m.get("name")
        ]
        if options:
            choice = st.selectbox("Set primary routing model", options, key="maker_ollama_primary")
            if st.button("Update primary", key="maker_ollama_primary_btn"):
                try:
                    ollama_svc.set_primary_routing(choice)
                    st.success(f"Primary set to {choice}")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

    models = data.get("models")
    if not isinstance(models, list) or not models:
        return

    for row in models:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if not name:
            continue
        is_primary = primary and name == primary
        line = f"- **{name}** ({_format_size(row.get('size_bytes'))})"
        if is_primary:
            line += " — *primary*"
        st.markdown(line)
        if allow_delete and st.button(f"Delete {name}", key=f"maker_ollama_del_{name}"):
            try:
                ollama_svc.delete_model(name)
                st.success(f"Deleted {name}")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
