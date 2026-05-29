"""Custom agent picker and pencil prompt editor (fo151)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

from nimbusware_config.persist import load_custom_agent_registry, persist_custom_agent_registry
from hermes_extensions.custom_agents import CustomAgent, CustomAgentRegistry

_SS_EDIT_AGENT = "nimbusware_edit_agent_id"
_SS_PROMPT_DRAFT = "nimbusware_prompt_draft"


def _api_base() -> str:
    return os.environ.get("NIMBUSWARE_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/")


def _admin_headers() -> dict[str, str]:
    token = os.environ.get("NIMBUSWARE_ADMIN_TOKEN", "").strip()
    return {"X-Nimbusware-Admin-Token": token} if token else {}


def load_registry_local(repo_root: Path) -> CustomAgentRegistry:
    return load_custom_agent_registry(repo_root)


def render_custom_agents_sidebar(repo_root: Path) -> str | None:
    """Sidebar: agent list, selection, pencil edit. Returns selected agent id."""
    st.header("Custom agents")
    reg = load_registry_local(repo_root)
    agents = reg.list()
    if not agents:
        st.caption("No agents in registry.")
        return None

    options = {f"{a.display_name} ({a.id})": a.id for a in agents}
    labels = list(options.keys())
    default_ix = 0
    choice = st.selectbox("Active agent", labels, index=default_ix)
    agent_id = options[choice]
    st.session_state["nimbusware_active_agent_id"] = agent_id

    agent = reg.get(agent_id)
    if agent is None:
        return agent_id

    st.caption(agent.description or "No description.")
    if st.button("✏️ Edit prompt", key=f"edit_prompt_{agent_id}", use_container_width=True):
        st.session_state[_SS_EDIT_AGENT] = agent_id
        st.session_state[_SS_PROMPT_DRAFT] = agent.system_prompt

    edit_id = st.session_state.get(_SS_EDIT_AGENT)
    if edit_id == agent_id:
        draft = st.text_area(
            "System prompt",
            value=st.session_state.get(_SS_PROMPT_DRAFT, agent.system_prompt),
            height=200,
            key=f"prompt_area_{agent_id}",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save", key=f"save_prompt_{agent_id}"):
                _save_prompt(repo_root, agent, draft)
                st.session_state.pop(_SS_EDIT_AGENT, None)
                st.success("Prompt saved.")
                st.rerun()
        with col2:
            if st.button("Cancel", key=f"cancel_prompt_{agent_id}"):
                st.session_state.pop(_SS_EDIT_AGENT, None)
                st.rerun()
    return agent_id


def _save_prompt(repo_root: Path, agent: CustomAgent, prompt: str) -> None:
    headers = _admin_headers()
    if headers:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.patch(
                    f"{_api_base()}/custom-agents/{agent.id}",
                    headers=headers,
                    json={
                        "display_name": agent.display_name,
                        "system_prompt": prompt,
                        "description": agent.description,
                        "bound_role_id": agent.bound_role_id,
                    },
                )
            if resp.status_code < 400:
                return
        except httpx.HTTPError:
            pass
    reg = load_registry_local(repo_root)
    updated = CustomAgent(
        id=agent.id,
        display_name=agent.display_name,
        system_prompt=prompt,
        description=agent.description,
        bound_role_id=agent.bound_role_id,
        version=agent.version,
    )
    reg.upsert(updated)
    persist_custom_agent_registry(repo_root, reg)
