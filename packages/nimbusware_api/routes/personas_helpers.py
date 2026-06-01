from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException

from agent_core.models import EventType
from hermes_extensions.personas import ALLOWED_SHELVES, PersonaShelf
from hermes_orchestrator.persona_catalog_audit import persona_catalog_run_id
from nimbusware_api.errors import problem
from nimbusware_api.schemas.personas import PersonaShelvesResponse
from nimbusware_config.persist import load_persona_shelf, persist_persona_shelf

_RESERVED_PERSONA_IDS = frozenset({"default"})


def config_materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


def load_shelf(orch: Any) -> PersonaShelf:
    """Load + structurally validate persona shelves; raise HTTPException on failure."""
    mat = config_materializer(orch)
    path = orch.repo_root / "configs" / "personas" / "shelves.yaml"
    try:
        shelf = load_persona_shelf(orch.repo_root, materializer=mat)
        shelf.validate_structure()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=problem(
                "persona_catalog_unavailable",
                "persona shelves are missing under the frozen repo root",
                details={"path": str(path)},
            ),
        ) from None
    except KeyError as exc:
        raise HTTPException(
            status_code=503,
            detail=problem(
                "persona_catalog_unavailable",
                "persona shelves document is missing in config store",
                details={"reason": str(exc)},
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=problem(
                "persona_catalog_invalid",
                "persona shelves failed structural validation",
                details={"path": str(path), "reason": str(exc)},
            ),
        ) from exc
    return shelf


def persist_shelf(orch: Any, shelf: PersonaShelf) -> None:
    persist_persona_shelf(
        orch.repo_root,
        shelf,
        materializer=config_materializer(orch),
    )


def validate_shelf_name(shelf: str) -> None:
    if shelf not in ALLOWED_SHELVES:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_shelf",
                f"shelf must be one of {list(ALLOWED_SHELVES)}",
                details={"shelf": shelf},
            ),
        )


def entry_version(entry: dict[str, Any] | None) -> int:
    """Treat missing or non-int ``version`` as 1 (matches ``to_public_catalog`` defaults)."""
    if not entry:
        return 0
    raw = entry.get("version")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
        return raw
    return 1


def find_replayed_event(
    store: Any, shelf: str, persona_id: str, idem_key: UUID,
) -> bool:
    """Return ``True`` when an existing ``persona.shelf.updated`` row matches ``idem_key``."""
    rid = str(persona_catalog_run_id(shelf, persona_id))
    for r in store.list_run_events(rid):
        if (
            r.get("event_type") == EventType.PERSONA_SHELF_UPDATED.value
            and str(r.get("correlation_id") or "") == str(idem_key)
        ):
            return True
    return False


def public_catalog(shelf: PersonaShelf) -> PersonaShelvesResponse:
    return PersonaShelvesResponse.model_validate(shelf.to_public_catalog())


def parse_idempotency_key(header: str | None) -> UUID | None:
    if header is None or not str(header).strip():
        return None
    try:
        return UUID(str(header).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "Idempotency-Key must be a UUID when set",
                details={"header": "Idempotency-Key"},
            ),
        ) from exc
