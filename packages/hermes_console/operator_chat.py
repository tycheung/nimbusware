"""Cursor-like operator chat for Nimbusware (fo150)."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

_SS_CHAT_MESSAGES = "nimbusware_chat_messages"
_SS_CHAT_THREAD = "nimbusware_chat_thread"
_SS_ACTIVE_AGENT = "nimbusware_active_agent_id"
_SS_LAST_RUN = "nimbusware_last_run_id"


def _api_base() -> str:
    return os.environ.get("HERMES_API_BASE", "http://127.0.0.1:8000/v1").rstrip("/")


def _ensure_chat_state() -> None:
    if _SS_CHAT_THREAD not in st.session_state:
        st.session_state[_SS_CHAT_THREAD] = str(uuid.uuid4())
    if _SS_CHAT_MESSAGES not in st.session_state:
        st.session_state[_SS_CHAT_MESSAGES] = [
            {
                "role": "assistant",
                "content": (
                    "Nimbusware operator chat. Ask me to start a run, show help, or pick "
                    "an agent in the sidebar. Commands: /help, /run [profile], /timeline."
                ),
            },
        ]


def _append_message(role: str, content: str) -> None:
    st.session_state[_SS_CHAT_MESSAGES].append(
        {"role": role, "content": content, "at": datetime.now(timezone.utc).isoformat()},
    )


def _handle_command(text: str) -> str | None:
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""
    if cmd in ("/help", "help"):
        return (
            "Commands:\n"
            "- /run [workflow_profile] — start a Hermes run (default: micro_slice)\n"
            "- /timeline — show last run id\n"
            "- /agent <id> — set active custom agent\n"
            "Or type natural language; I will suggest next steps."
        )
    if cmd == "/run":
        profile = parts[1] if len(parts) > 1 else "micro_slice"
        return _start_run(profile)
    if cmd == "/timeline":
        run_id = st.session_state.get(_SS_LAST_RUN)
        if not run_id:
            return "No run started yet. Use /run micro_slice first."
        return _fetch_timeline_summary(run_id)
    if cmd == "/agent" and len(parts) > 1:
        st.session_state[_SS_ACTIVE_AGENT] = parts[1]
        return f"Active agent set to `{parts[1]}`."
    if text.strip().lower().startswith("start run"):
        return _start_run("micro_slice")
    return None


def _start_run(workflow_profile: str) -> str:
    payload: dict[str, Any] = {"workflow_profile": workflow_profile}
    agent_id = st.session_state.get(_SS_ACTIVE_AGENT)
    if agent_id:
        payload["custom_agent_id"] = agent_id
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{_api_base()}/runs", json=payload)
        if resp.status_code >= 400:
            return f"Run failed ({resp.status_code}): {resp.text[:500]}"
        data = resp.json()
        run_id = data.get("run_id", "")
        st.session_state[_SS_LAST_RUN] = run_id
        return f"Started run `{run_id}` with profile `{workflow_profile}`."
    except httpx.HTTPError as exc:
        return f"Could not reach API at {_api_base()}: {exc}"


def _fetch_timeline_summary(run_id: str) -> str:
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{_api_base()}/runs/{run_id}/timeline")
        if resp.status_code >= 400:
            return f"Timeline fetch failed ({resp.status_code})."
        data = resp.json()
        ms = data.get("micro_slice") or {}
        if ms:
            return (
                f"Run `{run_id}` micro-slice: planned={ms.get('slice_count_planned')}, "
                f"completed={ms.get('slices_completed')}, blocked={ms.get('slices_blocked')}."
            )
        return f"Run `{run_id}` has {len(data.get('events', []))} events in timeline."
    except httpx.HTTPError as exc:
        return f"Timeline error: {exc}"


def process_user_message(text: str) -> str:
    reply = _handle_command(text)
    if reply is not None:
        return reply
    return (
        "I can start runs and show timelines. Try `/run micro_slice` or select an agent "
        "in the sidebar, then describe the change you want in small slices."
    )


def render_operator_chat(*, repo_root: Path | None = None) -> None:
    """Render chat UI in the main Streamlit column."""
    _ensure_chat_state()
    st.subheader("Operator chat")
    agent = st.session_state.get(_SS_ACTIVE_AGENT)
    if agent:
        st.caption(f"Active agent: `{agent}`")
    thread = st.session_state[_SS_CHAT_THREAD]
    st.caption(f"Thread: `{thread[:8]}…` · API: `{_api_base()}`")

    for msg in st.session_state[_SS_CHAT_MESSAGES]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Message Nimbusware…")
    if prompt:
        _append_message("user", prompt)
        reply = process_user_message(prompt)
        _append_message("assistant", reply)
        st.rerun()

    if repo_root is not None:
        log_dir = repo_root / ".cache" / "nimbusware_chat"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{thread}.jsonl"
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                for msg in st.session_state[_SS_CHAT_MESSAGES][-2:]:
                    handle.write(json.dumps(msg, ensure_ascii=False) + "\n")
        except OSError:
            pass
