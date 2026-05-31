"""Persona catalog HTTP API with optional editing surface.

GET stays unauthenticated (read-only catalog discovery); POST / PUT / PATCH /
DELETE require ``X-Nimbusware-Admin-Token`` since they mutate ``shelves.yaml`` and
emit a ``persona.shelf.updated`` audit event into the append-only store.

Optimistic concurrency: PATCH / PUT / DELETE all carry ``expected_version``
(int) that must match the on-disk ``version`` of the affected entry; mismatch
yields HTTP 409 ``persona_version_conflict``. POST honors ``Idempotency-Key``
(matches the ``POST /v1/runs`` precedent) — a replayed key returns the prior
catalog without appending a second event.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from agent_core.models import EventType
from hermes_extensions.personas import (
    ALLOWED_SHELVES,
    PersonaShelf,
    normalize_entry,
)
from hermes_orchestrator.persona_catalog_audit import (
    append_persona_shelf_updated_event,
    persona_catalog_run_id,
)
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PERSONA_ALREADY_EXISTS_409,
    PERSONA_DELETE_RESPONSE_204,
    PERSONA_UPSERT_RESPONSE_200,
    PERSONA_VERSION_CONFLICT_409,
    PERSONAS_RESPONSE_200,
    PROBLEM_RESPONSE_401,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    PROBLEM_RESPONSE_503,
)
from nimbusware_api.schemas.personas import (
    PersonaShelfPatchRequest,
    PersonaShelfUpsertRequest,
    PersonaShelvesResponse,
)
from nimbusware_config.persist import load_persona_shelf, persist_persona_shelf

router = APIRouter(prefix="/personas", tags=["personas"])

_RESERVED_PERSONA_IDS = frozenset({"default"})


def _config_materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


def _load_shelf(orch: Any) -> PersonaShelf:
    """Load + structurally validate persona shelves; raise HTTPException on failure."""
    mat = _config_materializer(orch)
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


def _persist_shelf(orch: Any, shelf: PersonaShelf) -> None:
    persist_persona_shelf(
        orch.repo_root,
        shelf,
        materializer=_config_materializer(orch),
    )


def _validate_shelf_name(shelf: str) -> None:
    if shelf not in ALLOWED_SHELVES:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_shelf",
                f"shelf must be one of {list(ALLOWED_SHELVES)}",
                details={"shelf": shelf},
            ),
        )


def _entry_version(entry: dict[str, Any] | None) -> int:
    """Treat missing or non-int ``version`` as 1 (matches ``to_public_catalog`` defaults)."""
    if not entry:
        return 0
    raw = entry.get("version")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1:
        return raw
    return 1


def _find_replayed_event(
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


def _public_catalog(shelf: PersonaShelf) -> PersonaShelvesResponse:
    return PersonaShelvesResponse.model_validate(shelf.to_public_catalog())


def _parse_idempotency_key(header: str | None) -> UUID | None:
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


@router.get(
    "",
    response_model=PersonaShelvesResponse,
    responses={200: PERSONAS_RESPONSE_200, 422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
    summary="List persona shelves",
)
def get_persona_shelves(orch: OrchDep) -> PersonaShelvesResponse:
    """Return read-only persona catalog from ``configs/personas/shelves.yaml``."""
    shelf = _load_shelf(orch)
    return _public_catalog(shelf)


@router.post(
    "/{shelf}",
    response_model=PersonaShelvesResponse,
    status_code=201,
    responses={
        201: PERSONA_UPSERT_RESPONSE_200,
        401: PROBLEM_RESPONSE_401,
        409: PERSONA_ALREADY_EXISTS_409,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Create a new persona on a shelf",
)
def create_persona(
    shelf: str,
    body: PersonaShelfUpsertRequest,
    orch: OrchDep,
    store: StoreDep,
    _admin: AdminDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> PersonaShelvesResponse:
    _validate_shelf_name(shelf)
    persona_id = body.entry.id.strip()
    if persona_id in _RESERVED_PERSONA_IDS:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "reserved_persona_id",
                f"persona_id {persona_id!r} is reserved by the orchestrator",
                details={"persona_id": persona_id},
            ),
        )
    idem = _parse_idempotency_key(idempotency_key)
    persona_shelf = _load_shelf(orch)
    if persona_shelf.find_entry(shelf, persona_id) is not None:
        if idem is not None and _find_replayed_event(store, shelf, persona_id, idem):
            return _public_catalog(persona_shelf)
        raise HTTPException(
            status_code=409,
            detail=problem(
                "persona_already_exists",
                f"persona {persona_id!r} already exists on shelf {shelf!r}",
                details={"shelf": shelf, "persona_id": persona_id},
            ),
        )
    new_entry = body.entry.model_dump(exclude_none=True)
    new_entry["version"] = 1
    new_entry["id"] = persona_id
    persona_shelf.write_entry(shelf, new_entry)
    _persist_shelf(orch, persona_shelf)
    append_persona_shelf_updated_event(
        store,
        shelf=shelf,
        persona_id=persona_id,
        prev_version=0,
        next_version=1,
        fields_changed=sorted(set(new_entry.keys()) - {"id", "version"}),
        actor=body.actor,
        correlation_id=idem,
    )
    return _public_catalog(persona_shelf)


@router.put(
    "/{shelf}/{persona_id}",
    response_model=PersonaShelvesResponse,
    responses={
        200: PERSONA_UPSERT_RESPONSE_200,
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        409: PERSONA_VERSION_CONFLICT_409,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Replace a persona entry (full upsert)",
)
def replace_persona(
    shelf: str,
    persona_id: str,
    body: PersonaShelfUpsertRequest,
    orch: OrchDep,
    store: StoreDep,
    _admin: AdminDep,
) -> PersonaShelvesResponse:
    _validate_shelf_name(shelf)
    if body.expected_version is None:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "expected_version_required",
                "PUT requires expected_version in the request body",
                details={"shelf": shelf, "persona_id": persona_id},
            ),
        )
    if body.entry.id.strip() != persona_id.strip():
        raise HTTPException(
            status_code=422,
            detail=problem(
                "persona_id_mismatch",
                "body.entry.id must match the path persona_id",
                details={"path": persona_id, "body": body.entry.id},
            ),
        )
    persona_shelf = _load_shelf(orch)
    existing = persona_shelf.find_entry(shelf, persona_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "persona_not_found",
                f"persona {persona_id!r} not found on shelf {shelf!r}",
                details={"shelf": shelf, "persona_id": persona_id},
            ),
        )
    prev_version = _entry_version(existing)
    if body.expected_version != prev_version:
        raise HTTPException(
            status_code=409,
            detail=problem(
                "persona_version_conflict",
                "expected_version does not match current version on disk",
                details={
                    "shelf": shelf,
                    "persona_id": persona_id,
                    "expected_version": body.expected_version,
                    "actual_version": prev_version,
                },
            ),
        )
    next_version = prev_version + 1
    new_entry = body.entry.model_dump(exclude_none=True)
    new_entry["id"] = persona_id
    new_entry["version"] = next_version
    persona_shelf.write_entry(shelf, new_entry)
    _persist_shelf(orch, persona_shelf)
    fields_changed = sorted(
        {k for k in new_entry if k not in {"id", "version"}}
        | {k for k in existing if k not in {"id", "version"}},
    )
    append_persona_shelf_updated_event(
        store,
        shelf=shelf,
        persona_id=persona_id,
        prev_version=prev_version,
        next_version=next_version,
        fields_changed=fields_changed,
        actor=body.actor,
        correlation_id=None,
    )
    return _public_catalog(persona_shelf)


@router.patch(
    "/{shelf}/{persona_id}",
    response_model=PersonaShelvesResponse,
    responses={
        200: PERSONA_UPSERT_RESPONSE_200,
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        409: PERSONA_VERSION_CONFLICT_409,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Partial update of a persona entry",
)
def patch_persona(
    shelf: str,
    persona_id: str,
    body: PersonaShelfPatchRequest,
    orch: OrchDep,
    store: StoreDep,
    _admin: AdminDep,
) -> PersonaShelvesResponse:
    _validate_shelf_name(shelf)
    persona_shelf = _load_shelf(orch)
    existing = persona_shelf.find_entry(shelf, persona_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "persona_not_found",
                f"persona {persona_id!r} not found on shelf {shelf!r}",
                details={"shelf": shelf, "persona_id": persona_id},
            ),
        )
    prev_version = _entry_version(existing)
    if body.expected_version != prev_version:
        raise HTTPException(
            status_code=409,
            detail=problem(
                "persona_version_conflict",
                "expected_version does not match current version on disk",
                details={
                    "shelf": shelf,
                    "persona_id": persona_id,
                    "expected_version": body.expected_version,
                    "actual_version": prev_version,
                },
            ),
        )
    mutated = body.mutated_fields()
    if not mutated:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "empty_patch",
                "PATCH body must include at least one mutable field",
                details={"shelf": shelf, "persona_id": persona_id},
            ),
        )
    next_version = prev_version + 1
    merged = dict(existing)
    body_dump = body.model_dump(exclude_unset=True, exclude={"expected_version", "actor"})
    merged.update(body_dump)
    merged["id"] = persona_id
    merged["version"] = next_version
    normalized = normalize_entry(merged)
    persona_shelf.write_entry(shelf, normalized)
    _persist_shelf(orch, persona_shelf)
    append_persona_shelf_updated_event(
        store,
        shelf=shelf,
        persona_id=persona_id,
        prev_version=prev_version,
        next_version=next_version,
        fields_changed=mutated,
        actor=body.actor,
        correlation_id=None,
    )
    return _public_catalog(persona_shelf)


@router.delete(
    "/{shelf}/{persona_id}",
    status_code=204,
    responses={
        204: PERSONA_DELETE_RESPONSE_204,
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        409: PERSONA_VERSION_CONFLICT_409,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Delete a persona entry",
)
def delete_persona(
    shelf: str,
    persona_id: str,
    orch: OrchDep,
    store: StoreDep,
    _admin: AdminDep,
    expected_version: int = Query(..., ge=1),
    actor: str | None = Query(default=None, max_length=200),
) -> None:
    _validate_shelf_name(shelf)
    persona_shelf = _load_shelf(orch)
    existing = persona_shelf.find_entry(shelf, persona_id)
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "persona_not_found",
                f"persona {persona_id!r} not found on shelf {shelf!r}",
                details={"shelf": shelf, "persona_id": persona_id},
            ),
        )
    prev_version = _entry_version(existing)
    if expected_version != prev_version:
        raise HTTPException(
            status_code=409,
            detail=problem(
                "persona_version_conflict",
                "expected_version does not match current version on disk",
                details={
                    "shelf": shelf,
                    "persona_id": persona_id,
                    "expected_version": expected_version,
                    "actual_version": prev_version,
                },
            ),
        )
    persona_shelf.delete_entry(shelf, persona_id)
    _persist_shelf(orch, persona_shelf)
    append_persona_shelf_updated_event(
        store,
        shelf=shelf,
        persona_id=persona_id,
        prev_version=prev_version,
        next_version=prev_version + 1,
        fields_changed=["__deleted__"],
        actor=actor,
        correlation_id=None,
    )
