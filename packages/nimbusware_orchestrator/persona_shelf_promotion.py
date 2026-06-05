"""Persona shelf promotion after the agent evaluator stage."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from agent_core.models import EventType
from nimbusware_extensions.personas import ALLOWED_SHELVES
from nimbusware_orchestrator.persona_catalog_audit import (
    append_persona_shelf_updated_event,
    persona_catalog_run_id,
)
from nimbusware_store.protocol import EventStore
from nimbusware_config.persist import load_persona_shelf, persist_persona_shelf

_AUTO_PROMOTE_CORR_NAMESPACE = UUID("00000000-0000-5000-8000-000000000002")
_AUTO_SHELVE_CORR_NAMESPACE = UUID("00000000-0000-5000-8000-000000000004")


def auto_promote_probation_correlation_id(run_id: UUID, persona_id: str) -> UUID:
    """Deterministic idempotency key for a single run + evaluated persona."""
    return uuid5(_AUTO_PROMOTE_CORR_NAMESPACE, f"{run_id}:{persona_id}")


def _entry_version(entry: dict[str, Any] | None) -> int:
    if not entry:
        return 0
    raw = entry.get("version")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
        return raw
    return 1


def _persona_event_replayed(
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


def try_auto_promote_probation_persona(
    repo_root: Path,
    store: EventStore,
    *,
    persona_id: str,
    run_id: UUID,
    config_materializer: Any | None = None,
    actor: str = "system:agent_evaluator",
) -> dict[str, Any]:
    """If ``persona_id`` exists on a shelf with ``probation_status: probation``, bump to promoted.

    Writes ``configs/personas/shelves.yaml`` atomically and appends
    ``persona.shelf.updated`` with ``actor`` (default ``system:agent_evaluator``).

    Returns JSON-safe metadata for ``stage.started`` envelope ``metadata``.
    """
    if not persona_id.strip() or persona_id.strip() == "default":
        return {
            "auto_promote_probation_applied": False,
            "reason": "default_persona_slot",
        }

    corr = auto_promote_probation_correlation_id(run_id, persona_id.strip())
    try:
        shelf_obj = load_persona_shelf(repo_root, materializer=config_materializer)
    except (FileNotFoundError, KeyError):
        return {
            "auto_promote_probation_applied": False,
            "reason": "persona_catalog_missing",
        }
    try:
        shelf_obj.validate_structure()
    except ValueError as exc:
        return {
            "auto_promote_probation_applied": False,
            "reason": "persona_catalog_invalid",
            "detail": str(exc)[:500],
        }

    found_shelf: str | None = None
    found_entry: dict[str, Any] | None = None
    for sk in ALLOWED_SHELVES:
        ent = shelf_obj.find_entry(sk, persona_id.strip())
        if ent is not None:
            found_shelf = sk
            found_entry = ent
            break

    if found_shelf is None or found_entry is None:
        return {
            "auto_promote_probation_applied": False,
            "reason": "persona_not_found",
        }

    if _persona_event_replayed(
        store,
        shelf=found_shelf,
        persona_id=persona_id.strip(),
        correlation_id=corr,
    ):
        return {
            "auto_promote_probation_applied": False,
            "reason": "already_recorded",
            "shelf": found_shelf,
        }

    ps = str(found_entry.get("probation_status") or "").strip().lower()
    if ps != "probation":
        return {
            "auto_promote_probation_applied": False,
            "reason": "not_on_probation",
            "shelf": found_shelf,
            "probation_status": ps or None,
        }

    prev_v = _entry_version(found_entry)
    merged = dict(found_entry)
    merged["probation_status"] = "promoted"
    merged["version"] = prev_v + 1
    shelf_obj.write_entry(found_shelf, merged)
    try:
        shelf_obj.validate_structure()
    except ValueError as exc:
        return {
            "auto_promote_probation_applied": False,
            "reason": "promoted_entry_invalid",
            "detail": str(exc)[:500],
        }

    persist_persona_shelf(repo_root, shelf_obj, materializer=config_materializer)
    append_persona_shelf_updated_event(
        store,
        shelf=found_shelf,
        persona_id=persona_id.strip(),
        prev_version=prev_v,
        next_version=prev_v + 1,
        fields_changed=["probation_status", "version"],
        actor=actor,
        correlation_id=corr,
    )
    return {
        "auto_promote_probation_applied": True,
        "shelf": found_shelf,
        "prev_version": prev_v,
        "next_version": prev_v + 1,
    }


def auto_shelve_probation_correlation_id(run_id: UUID, persona_id: str) -> UUID:
    """Deterministic idempotency key for a single run + shelved persona."""
    return uuid5(_AUTO_SHELVE_CORR_NAMESPACE, f"{run_id}:{persona_id}")


def try_auto_shelve_probation_persona(
    repo_root: Path,
    store: EventStore,
    *,
    persona_id: str,
    run_id: UUID,
    config_materializer: Any | None = None,
    actor: str = "system:agent_evaluator",
) -> dict[str, Any]:
    """If ``persona_id`` exists on a shelf with ``probation_status: probation``, set ``shelved``.

    Writes ``configs/personas/shelves.yaml`` atomically and appends
    ``persona.shelf.updated`` with ``actor`` (default ``system:agent_evaluator``).

    Returns JSON-safe metadata for ``stage.started`` envelope ``metadata``.
    """
    if not persona_id.strip() or persona_id.strip() == "default":
        return {
            "auto_shelve_probation_applied": False,
            "reason": "default_persona_slot",
        }

    corr = auto_shelve_probation_correlation_id(run_id, persona_id.strip())
    try:
        shelf_obj = load_persona_shelf(repo_root, materializer=config_materializer)
    except (FileNotFoundError, KeyError):
        return {
            "auto_shelve_probation_applied": False,
            "reason": "persona_catalog_missing",
        }
    try:
        shelf_obj.validate_structure()
    except ValueError as exc:
        return {
            "auto_shelve_probation_applied": False,
            "reason": "persona_catalog_invalid",
            "detail": str(exc)[:500],
        }

    found_shelf: str | None = None
    found_entry: dict[str, Any] | None = None
    for sk in ALLOWED_SHELVES:
        ent = shelf_obj.find_entry(sk, persona_id.strip())
        if ent is not None:
            found_shelf = sk
            found_entry = ent
            break

    if found_shelf is None or found_entry is None:
        return {
            "auto_shelve_probation_applied": False,
            "reason": "persona_not_found",
        }

    if _persona_event_replayed(
        store,
        shelf=found_shelf,
        persona_id=persona_id.strip(),
        correlation_id=corr,
    ):
        return {
            "auto_shelve_probation_applied": False,
            "reason": "already_recorded",
            "shelf": found_shelf,
        }

    ps = str(found_entry.get("probation_status") or "").strip().lower()
    if ps != "probation":
        return {
            "auto_shelve_probation_applied": False,
            "reason": "not_on_probation",
            "shelf": found_shelf,
            "probation_status": ps or None,
        }

    prev_v = _entry_version(found_entry)
    merged = dict(found_entry)
    merged["probation_status"] = "shelved"
    merged["version"] = prev_v + 1
    shelf_obj.write_entry(found_shelf, merged)
    try:
        shelf_obj.validate_structure()
    except ValueError as exc:
        return {
            "auto_shelve_probation_applied": False,
            "reason": "shelved_entry_invalid",
            "detail": str(exc)[:500],
        }

    persist_persona_shelf(repo_root, shelf_obj, materializer=config_materializer)
    append_persona_shelf_updated_event(
        store,
        shelf=found_shelf,
        persona_id=persona_id.strip(),
        prev_version=prev_v,
        next_version=prev_v + 1,
        fields_changed=["probation_status", "version"],
        actor=actor,
        correlation_id=corr,
    )
    return {
        "auto_shelve_probation_applied": True,
        "shelf": found_shelf,
        "prev_version": prev_v,
        "next_version": prev_v + 1,
    }
