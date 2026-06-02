from __future__ import annotations

import streamlit as st

from nimbusware_console.pages.config_tooling.ollama_models._format import format_size
from nimbusware_console.services import ollama as ollama_svc


def render_ollama_models_section() -> None:
    st.subheader("Ollama models")
    st.caption(
        "Installed models on the configured Ollama runtime. Admins can pull or delete any model; "
        "toggle which actions Maker users may perform under **User policy**.",
    )

    if "ollama_models_query" not in st.session_state:
        st.session_state["ollama_models_query"] = ""

    query = st.text_input(
        "Search installed models",
        key="ollama_models_query",
        placeholder="e.g. llama, qwen",
    )

    try:
        data = ollama_svc.list_models(query=query)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load Ollama models: {exc}")
        return

    reachable = bool(data.get("reachable"))
    base_url = str(data.get("base_url") or "")
    primary = data.get("primary_model_id")
    policy = data.get("user_policy") if isinstance(data.get("user_policy"), dict) else {}

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Ollama reachable", "yes" if reachable else "no")
    with col_b:
        st.metric("Primary routing model", str(primary or "—"))

    st.caption(f"Runtime: `{base_url}`")

    with st.expander("Maker user policy", expanded=True):
        st.caption("Controls policy-gated **POST /platform/ollama/** routes for Maker users.")
        c1, c2, c3 = st.columns(3)
        with c1:
            allow_pull = st.checkbox(
                "Users may pull models",
                value=bool(policy.get("allow_pull")),
                key="ollama_policy_allow_pull",
            )
        with c2:
            allow_delete = st.checkbox(
                "Users may delete models",
                value=bool(policy.get("allow_delete")),
                key="ollama_policy_allow_delete",
            )
        with c3:
            allow_routing = st.checkbox(
                "Users may change primary routing",
                value=bool(policy.get("allow_update_routing")),
                key="ollama_policy_allow_routing",
            )
        if st.button("Save user policy", key="ollama_save_user_policy"):
            try:
                saved = ollama_svc.save_user_policy(
                    allow_pull=allow_pull,
                    allow_delete=allow_delete,
                    allow_update_routing=allow_routing,
                )
                st.success(
                    "Saved user policy: "
                    f"pull={saved.get('allow_pull')} "
                    f"delete={saved.get('allow_delete')} "
                    f"routing={saved.get('allow_update_routing')}",
                )
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Failed to save policy: {exc}")

    pull_name = st.text_input(
        "Pull model (admin)",
        key="ollama_admin_pull_name",
        placeholder="llama3.1:8b",
    )
    if st.button("Pull model", key="ollama_admin_pull_btn") and pull_name.strip():
        try:
            ollama_svc.admin_pull_model(pull_name.strip())
            st.success(f"Pulled {pull_name.strip()}")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Pull failed: {exc}")

    models = data.get("models")
    if not isinstance(models, list) or not models:
        if not reachable:
            st.warning(
                "Ollama is not reachable — start Ollama or check `configs/model-routing.yaml`."
            )
        else:
            st.info("No installed models match your search.")
        return

    for row in models:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        if not name:
            continue
        size = format_size(row.get("size_bytes"))
        modified = str(row.get("modified_at") or "")
        is_primary = primary and name == primary
        label = f"**{name}**" + (" *(primary)*" if is_primary else "")
        with st.container(border=True):
            st.markdown(label)
            st.caption(f"Size: {size}" + (f" · modified {modified}" if modified else ""))
            if st.button(f"Delete {name}", key=f"ollama_del_{name}"):
                try:
                    ollama_svc.admin_delete_model(name)
                    st.success(f"Deleted {name}")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Delete failed: {exc}")
