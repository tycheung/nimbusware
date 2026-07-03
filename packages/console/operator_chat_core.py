from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from client.http import HTTPError, api_base
from console.services import operator_chat as chat_svc

WORK_TYPE_PROFILES: dict[str, str] = {
    "patch": "patch",
    "slice": "micro_slice",
    "campaign": "campaign_micro_slice",
    "factory": "campaign_factory_zero_touch",
    "quick": "quick_local",
}


@dataclass
class ChatState:
    last_run_id: str = ""
    active_agent_id: str = ""
    memory_retrieval_enabled: bool = True
    memory_index_contribution: bool = True
    messages: list[dict[str, str]] = field(default_factory=list)
    suggested_profile: str = ""
    last_intent_text: str = ""
    last_classification: dict[str, Any] | None = None


def process_user_message(text: str, state: ChatState) -> str:
    reply = _handle_command(text, state)
    if reply is not None:
        return reply
    classification = _classify_intent(text)
    if classification:
        work_type = str(classification.get("work_type") or "slice")
        profile = WORK_TYPE_PROFILES.get(work_type, "micro_slice")
        state.suggested_profile = profile
        state.last_intent_text = text
        state.last_classification = classification
        confidence = float(classification.get("confidence") or 0)
        rationale = str(classification.get("rationale") or "").strip()
        hint = f"{rationale} " if rationale else ""
        return (
            f"Suggested {work_type} → `{profile}` ({confidence:.0%}). {hint}"
            "Use `/run auto` to start or `/run <profile>` to override."
        )
    return (
        "I can classify intent and start runs. Try describing your change, then `/run auto`, "
        "or `/run micro_slice` directly."
    )


def _classify_intent(text: str) -> dict[str, Any] | None:
    try:
        resp = chat_svc.classify_intent(text.strip())
        if resp.status_code >= 400:
            return None
        body = resp.json()
        data = body.get("classification") if isinstance(body, dict) else None
        return data if isinstance(data, dict) else None
    except HTTPError:
        return None


def _handle_command(text: str, state: ChatState) -> str | None:
    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""
    if cmd in ("/help", "help"):
        return (
            "Commands:\n- /run [profile|auto]\n- /timeline\n- /status\n- /agent <id>\n"
            "Steer an active run with [patch], [steer], [skip], or [build] prefixes.\n"
            "Route to a discipline with @frontend, @backend, @qa, … when a run is active.\n"
            "Describe a change in plain language for intent classification."
        )
    if cmd == "/status":
        if not state.last_run_id:
            return "No run started yet. Use /run micro_slice first."
        return _fetch_run_status(state.last_run_id)
    if cmd == "/run":
        if len(parts) > 1 and parts[1].lower() == "auto":
            profile = state.suggested_profile or "micro_slice"
            return _start_run(profile, state)
        profile = parts[1] if len(parts) > 1 else "micro_slice"
        return _start_run(profile, state)
    if cmd == "/timeline":
        if not state.last_run_id:
            return "No run started yet. Use /run micro_slice first."
        return _fetch_timeline_summary(state.last_run_id)
    if cmd == "/agent" and len(parts) > 1:
        state.active_agent_id = parts[1]
        return f"Active agent set to `{parts[1]}`."
    stripped = text.strip()
    low_prefix = stripped.lower()
    for prefix in ("[patch]", "[steer]", "[skip]", "[build]"):
        if low_prefix.startswith(prefix):
            if not state.last_run_id:
                return "No active run — use `/run` first, then send steering messages."
            return _enqueue_steering(state.last_run_id, stripped)
    if state.last_run_id and _message_has_routable_mentions(stripped):
        return _enqueue_steering(state.last_run_id, stripped)
    low = text.strip().lower()
    if low.startswith("start run") or ("micro_slice" in low and ("start" in low or "run" in low)):
        return _start_run("micro_slice", state)
    if low.startswith("show timeline") or low.startswith("timeline"):
        if not state.last_run_id:
            return "No run yet. Try `/run micro_slice`."
        return _fetch_timeline_summary(state.last_run_id)
    return None


def _message_has_routable_mentions(message: str) -> bool:
    from maker.collab.disciplines import parse_discipline_mentions
    from orchestrator.surface_interjection_routing import parse_surface_mentions

    return bool(parse_discipline_mentions(message) or parse_surface_mentions(message))


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


def _enqueue_steering(run_id: str, message: str) -> str:
    try:
        resp = chat_svc.enqueue_interjection(run_id, message)
        if resp.status_code >= 400:
            return f"Interjection failed ({resp.status_code}): {resp.text[:500]}"
        data = resp.json()
        count = int((data.get("queue") or {}).get("count") or 0)
        return f"Queued on run `{run_id}` ({count} item(s) pending)."
    except HTTPError as exc:
        return f"Could not reach API at {api_base()}: {exc}"


def _fetch_run_status(run_id: str) -> str:
    try:
        q_resp = chat_svc.fetch_interjection_queue(run_id)
        if q_resp.status_code >= 400:
            return f"Status fetch failed ({q_resp.status_code})."
        q_body = q_resp.json()
        pending = int((q_body.get("queue") or {}).get("count") or 0)
        tl = _fetch_timeline_summary(run_id)
        return f"Run `{run_id}` — interjection queue: {pending} pending.\n{tl}"
    except HTTPError as exc:
        return f"Status error: {exc}"


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
