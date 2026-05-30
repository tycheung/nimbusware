from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st

from nimbusware_client.http import HTTPError

from nimbusware_client.http import (
    api_base,
    get_response,
    post_response,
    user_headers,
)

_SS_CHAT_MESSAGES = "nimbusware_chat_messages"
_SS_CHAT_THREAD = "nimbusware_chat_thread"
_SS_ACTIVE_AGENT = "nimbusware_active_agent_id"
_SS_LAST_RUN = "nimbusware_last_run_id"
_SS_MEMORY_RETRIEVAL = "nimbusware_memory_retrieval_enabled"
_SS_MEMORY_CONTRIB = "nimbusware_memory_index_contribution"


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
    low = text.strip().lower()
    if low.startswith("run with agent ") or low.startswith("start run with agent "):
        agent = text.strip().split()[-1]
        st.session_state[_SS_ACTIVE_AGENT] = agent
        return _start_run("micro_slice")
    if "micro_slice" in low and ("start" in low or "run" in low):
        return _start_run("micro_slice")
    if low.startswith("show timeline") or low.startswith("timeline"):
        run_id = st.session_state.get(_SS_LAST_RUN)
        if not run_id:
            return "No run yet. Try `/run micro_slice`."
        return _fetch_timeline_summary(run_id)
    return None


def _start_run(workflow_profile: str) -> str:
    payload: dict[str, Any] = {"workflow_profile": workflow_profile}
    agent_id = st.session_state.get(_SS_ACTIVE_AGENT)
    if agent_id:
        payload["custom_agent_id"] = agent_id
    if _SS_MEMORY_RETRIEVAL in st.session_state:
        payload["memory_retrieval_enabled"] = bool(st.session_state[_SS_MEMORY_RETRIEVAL])
    if _SS_MEMORY_CONTRIB in st.session_state:
        payload["memory_index_contribution"] = bool(st.session_state[_SS_MEMORY_CONTRIB])
    try:
        resp = post_response(
            "/runs",
            payload=payload,
            headers=user_headers(),
            timeout=30.0,
            raise_for_status=False,
        )
        if resp.status_code >= 400:
            return f"Run failed ({resp.status_code}): {resp.text[:500]}"
        data = resp.json()
        run_id = data.get("run_id", "")
        st.session_state[_SS_LAST_RUN] = run_id
        return f"Started run `{run_id}` with profile `{workflow_profile}`."
    except HTTPError as exc:
        return f"Could not reach API at {api_base()}: {exc}"


def _fetch_timeline_summary(run_id: str) -> str:
    try:
        resp = get_response(
            f"/runs/{run_id}/timeline",
            headers=user_headers(),
            timeout=30.0,
            raise_for_status=False,
        )
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
    except HTTPError as exc:
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
    _ensure_chat_state()
    st.subheader("Operator chat")
    agent = st.session_state.get(_SS_ACTIVE_AGENT)
    if agent:
        st.caption(f"Active agent: `{agent}`")
    thread = st.session_state[_SS_CHAT_THREAD]
    st.caption(f"Thread: `{thread[:8]}…` · API: `{api_base()}`")
    st.checkbox(
        "Memory retrieval enabled for /run",
        value=st.session_state.get(_SS_MEMORY_RETRIEVAL, True),
        key=_SS_MEMORY_RETRIEVAL,
        help="Maps to POST /v1/runs memory_retrieval_enabled",
    )
    st.checkbox(
        "Contribute this run to memory index",
        value=st.session_state.get(_SS_MEMORY_CONTRIB, True),
        key=_SS_MEMORY_CONTRIB,
        help="Maps to POST /v1/runs memory_index_contribution",
    )

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
