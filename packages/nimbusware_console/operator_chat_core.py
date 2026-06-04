from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nimbusware_client.http import HTTPError, api_base
from nimbusware_console.services import operator_chat as chat_svc


@dataclass
class ChatState:
    last_run_id: str = ""
    active_agent_id: str = ""
    memory_retrieval_enabled: bool = True
    memory_index_contribution: bool = True
    messages: list[dict[str, str]] = field(default_factory=list)


def process_user_message(text: str, state: ChatState) -> str:
    reply = _handle_command(text, state)
    if reply is not None:
        return reply
    return (
        "I can start runs and show timelines. Try `/run micro_slice` or set an agent, "
        "then describe the change you want in small slices."
    )


def _handle_command(text: str, state: ChatState) -> str | None:
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""
    if cmd in ("/help", "help"):
        return "Commands:\n- /run [workflow_profile]\n- /timeline\n- /agent <id>"
    if cmd == "/run":
        profile = parts[1] if len(parts) > 1 else "micro_slice"
        return _start_run(profile, state)
    if cmd == "/timeline":
        if not state.last_run_id:
            return "No run started yet. Use /run micro_slice first."
        return _fetch_timeline_summary(state.last_run_id)
    if cmd == "/agent" and len(parts) > 1:
        state.active_agent_id = parts[1]
        return f"Active agent set to `{parts[1]}`."
    low = text.strip().lower()
    if low.startswith("start run") or ("micro_slice" in low and ("start" in low or "run" in low)):
        return _start_run("micro_slice", state)
    if low.startswith("show timeline") or low.startswith("timeline"):
        if not state.last_run_id:
            return "No run yet. Try `/run micro_slice`."
        return _fetch_timeline_summary(state.last_run_id)
    return None


def _start_run(workflow_profile: str, state: ChatState) -> str:
    payload: dict[str, Any] = {"workflow_profile": workflow_profile}
    if state.active_agent_id:
        payload["custom_agent_id"] = state.active_agent_id
    payload["memory_retrieval_enabled"] = state.memory_retrieval_enabled
    payload["memory_index_contribution"] = state.memory_index_contribution
    try:
        resp = chat_svc.create_run(payload)
        if resp.status_code >= 400:
            return f"Run failed ({resp.status_code}): {resp.text[:500]}"
        data = resp.json()
        run_id = str(data.get("run_id", ""))
        state.last_run_id = run_id
        return f"Started run `{run_id}` with profile `{workflow_profile}`."
    except HTTPError as exc:
        return f"Could not reach API at {api_base()}: {exc}"


def _fetch_timeline_summary(run_id: str) -> str:
    try:
        resp = chat_svc.fetch_timeline_response(run_id)
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
