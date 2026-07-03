from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from agent_core.models import EventType
from config.persist import load_persona_shelf, persist_persona_shelf
from extensions.personas import ALLOWED_SHELVES, normalize_entry
from orchestrator.persona.catalog_audit import (
    append_persona_shelf_updated_event,
    persona_catalog_run_id,
)
from orchestrator.workflow.agent_evaluator import AgentEvaluatorAutoCreatePersonaBlock
from store.protocol import EventStore

_ORCH_RESERVED_PERSONA_IDS = frozenset({"default"})
_AUTO_CREATE_CORR_NAMESPACE = UUID("00000000-0000-5000-8000-000000000003")
_DISPLAY_NAME_MAX = 200


def auto_create_persona_correlation_id(run_id: UUID, shelf: str, persona_id: str) -> UUID:
    return uuid5(_AUTO_CREATE_CORR_NAMESPACE, f"{run_id}:{shelf}:{persona_id}")


def _persona_create_event_replayed(
    store: EventStore,
    *,
    shelf: str,
    persona_id: str,
    correlation_id: UUID,
) -> bool:
    rid = str(persona_catalog_run_id(shelf, persona_id))
    for r in store.list_run_events(rid):
        if r.get("event_type") == EventType.PERSONA_SHELF_UPDATED.value and str(
            r.get("correlation_id") or ""
        ) == str(correlation_id):
            return True
    return False


def try_auto_create_persona_if_missing(
    repo_root: Path,
    store: EventStore,
    *,
    persona_id: str,
    run_id: UUID,
    cfg: AgentEvaluatorAutoCreatePersonaBlock,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    """Append a minimal persona row when ``cfg.enabled`` and id is absent from shelves.

    Uses the same atomic YAML + ``persona.shelf.updated`` path as ``POST /v1/personas``.
    """
    if not cfg.enabled:
        return {"auto_create_persona_applied": False, "reason": "disabled"}
    pid = str(persona_id).strip()
    if not pid or pid in _ORCH_RESERVED_PERSONA_IDS:
        return {
            "auto_create_persona_applied": False,
            "reason": "reserved_or_empty_persona_id",
        }
    shelf = str(cfg.shelf).strip()
    if shelf not in ALLOWED_SHELVES:
        return {
            "auto_create_persona_applied": False,
            "reason": "invalid_shelf",
            "shelf": shelf or None,
        }
    display = str(cfg.display_name).strip()
    if not display:
        return {
            "auto_create_persona_applied": False,
            "reason": "empty_display_name",
        }
    if len(display) > _DISPLAY_NAME_MAX:
        return {
            "auto_create_persona_applied": False,
            "reason": "display_name_too_long",
        }

    try:
        shelf_obj = load_persona_shelf(repo_root, materializer=config_materializer)
    except (FileNotFoundError, KeyError):
        return {
            "auto_create_persona_applied": False,
            "reason": "persona_catalog_missing",
        }
    try:
        shelf_obj.validate_structure()
    except ValueError as exc:
        return {
            "auto_create_persona_applied": False,
            "reason": "persona_catalog_invalid",
            "detail": str(exc)[:500],
        }

    if pid in shelf_obj.all_persona_ids():
        return {"auto_create_persona_applied": False, "reason": "already_exists"}

    corr = auto_create_persona_correlation_id(run_id, shelf, pid)
    if _persona_create_event_replayed(store, shelf=shelf, persona_id=pid, correlation_id=corr):
        return {
            "auto_create_persona_applied": False,
            "reason": "already_recorded",
            "shelf": shelf,
        }

    new_entry = normalize_entry({"id": pid, "display_name": display, "version": 1})
    shelf_obj.write_entry(shelf, new_entry)
    try:
        shelf_obj.validate_structure()
    except ValueError as exc:
        return {
            "auto_create_persona_applied": False,
            "reason": "new_entry_invalid",
            "detail": str(exc)[:500],
        }

    persist_persona_shelf(repo_root, shelf_obj, materializer=config_materializer)
    append_persona_shelf_updated_event(
        store,
        shelf=shelf,
        persona_id=pid,
        prev_version=0,
        next_version=1,
        fields_changed=sorted(set(new_entry.keys()) - {"id", "version"}),
        actor="system:agent_evaluator",
        correlation_id=corr,
    )
    return {
        "auto_create_persona_applied": True,
        "shelf": shelf,
        "persona_id": pid,
    }
