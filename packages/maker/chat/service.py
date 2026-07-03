from __future__ import annotations

from typing import Any

from maker.chat.session_models import ChatSessionRecord, ChatTurnRecord
from maker.chat.session_store import ChatStore, turns_to_legacy_messages
from maker.intent.classifier import ClassificationResult, WorkType
from maker.intent.requirements import build_requirements_artifact


def session_response(
    store: ChatStore,
    session: ChatSessionRecord,
    *,
    include_turns: bool = False,
) -> dict[str, Any]:
    path = store.get_active_path(session.session_id)
    messages = turns_to_legacy_messages(path)
    out: dict[str, Any] = {
        "session_id": str(session.session_id),
        "project_id": str(session.project_id),
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "title": session.title,
        "messages": messages,
        "turns": [t.to_dict() for t in path] if include_turns else None,
        "active_leaf_turn_id": (
            str(session.active_leaf_turn_id) if session.active_leaf_turn_id else None
        ),
        "last_classification": session.last_classification,
        "work_type_override": session.work_type_override,
        "run_id": str(session.run_id) if session.run_id else None,
        "campaign_id": str(session.campaign_id) if session.campaign_id else None,
        "host_user_id": str(session.host_user_id) if session.host_user_id else None,
        "workload_distribution": session.workload_distribution,
        "folder_id": str(session.folder_id) if session.folder_id else None,
        "tags": list(session.tags),
        "metadata": dict(session.metadata or {}),
    }
    if not include_turns:
        out.pop("turns")
    return out


def classification_dict(result: ClassificationResult) -> dict[str, Any]:
    return result.to_dict()


def requirements_from_path(path: list[ChatTurnRecord]) -> dict[str, Any] | None:
    for turn in reversed(path):
        if turn.role == "user" and turn.text.strip():
            return build_requirements_artifact(business_prompt=turn.text)
    return None


def patch_context_from_session(
    session: ChatSessionRecord, path: list[ChatTurnRecord]
) -> dict[str, Any] | None:
    from orchestrator.patch_context import normalize_patch_context

    extracted = (session.last_classification or {}).get("attachments_extracted")
    if extracted:
        return normalize_patch_context(extracted)
    for turn in reversed(path):
        if turn.role == "user":
            attachments = turn.payload.get("attachments")
            if isinstance(attachments, list) and attachments:
                return normalize_patch_context(attachments[0])
    return None


def resolve_work_type_source(
    explicit: str | None, session: ChatSessionRecord, *, mode_switch: bool = False
) -> str:
    raw = (explicit or "").strip().lower()
    if raw in {"classifier", "operator_override", "ide", "mode_switch"}:
        return raw
    if mode_switch:
        return "mode_switch"
    if session.work_type_override:
        return "operator_override"
    return "classifier"


def resolve_work_type(
    explicit: str | None,
    session: ChatSessionRecord,
) -> WorkType:
    raw = (explicit or session.work_type_override or "").strip().lower()
    if not raw and session.last_classification:
        raw = str(session.last_classification.get("work_type") or "").strip().lower()
    try:
        return WorkType(raw)
    except ValueError as exc:
        raise ValueError("work_type must be one of quick, patch, slice, campaign, factory") from exc


def switch_mode_rationale(from_wt: str | None, to_wt: str) -> str:
    src = from_wt or "auto"
    return f"Switched work type from {src} to {to_wt}."
