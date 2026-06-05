from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from nimbusware_extensions.persona_scope_overlap import persona_scope_overlap_report
from nimbusware_extensions.personas import normalize_entry
from nimbusware_extensions.phase2 import AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD
from nimbusware_orchestrator.persona_catalog_audit import append_persona_shelf_updated_event
from nimbusware_orchestrator.persona_probation_reliability import (
    collect_persona_eval_metrics,
    reliability_decision,
)
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.personas_helpers import (
    _RESERVED_PERSONA_IDS,
    entry_version,
    find_replayed_event,
    load_shelf,
    parse_idempotency_key,
    persist_shelf,
    public_catalog,
    validate_shelf_name,
)
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
    ProbationReliabilityResponse,
)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get(
    "",
    response_model=PersonaShelvesResponse,
    responses={200: PERSONAS_RESPONSE_200, 422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
    summary="List persona shelves",
)
def get_persona_shelves(orch: OrchDep) -> PersonaShelvesResponse:
    """Return read-only persona catalog from ``configs/personas/shelves.yaml``."""
    shelf = load_shelf(orch)
    return public_catalog(shelf)


@router.get(
    "/overlap-report",
    responses={200: PERSONAS_RESPONSE_200, 401: PROBLEM_RESPONSE_401, 500: PROBLEM_RESPONSE_500},
    summary="Persona scope_in overlap report",
)
def get_persona_overlap_report(orch: OrchDep, _admin: AdminDep) -> dict:
    shelf = load_shelf(orch)
    rows = persona_scope_overlap_report(shelf)
    warning = None
    if rows:
        warning = (
            f"{len(rows)} BA×DR pair(s) share scope_in tags — review shelf assignments before runs."
        )
    return {"pair_count": len(rows), "rows": rows, "warning": warning}


@router.get(
    "/{shelf}/{persona_id}/probation-reliability",
    response_model=ProbationReliabilityResponse,
    responses={200: PERSONAS_RESPONSE_200, 404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    summary="Probation reliability metrics for a persona",
)
def get_persona_probation_reliability(
    shelf: str,
    persona_id: str,
    store: StoreDep,
    orch: OrchDep,
    run_limit: int = Query(default=20, ge=1, le=200),
    min_eval_runs: int = Query(default=2, ge=1, le=100),
    min_score: float = Query(
        default=AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
    ),
    max_below_ratio: float = Query(default=0.5, ge=0.0, le=1.0),
) -> ProbationReliabilityResponse:
    validate_shelf_name(shelf)
    persona_shelf = load_shelf(orch)
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
    metrics = collect_persona_eval_metrics(store, persona_id, run_limit=run_limit)
    decision = reliability_decision(
        metrics,
        min_runs=min_eval_runs,
        min_score=min_score,
        max_below_ratio=max_below_ratio,
    )
    return ProbationReliabilityResponse(
        persona_id=metrics.persona_id,
        runs_evaluated=metrics.runs_evaluated,
        avg_score=metrics.avg_score,
        below_threshold_count=metrics.below_threshold_count,
        invalid_status_count=metrics.invalid_status_count,
        decision=decision,
        min_eval_runs=min_eval_runs,
        min_score=min_score,
        max_below_ratio=max_below_ratio,
    )


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
    validate_shelf_name(shelf)
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
    idem = parse_idempotency_key(idempotency_key)
    persona_shelf = load_shelf(orch)
    if persona_shelf.find_entry(shelf, persona_id) is not None:
        if idem is not None and find_replayed_event(store, shelf, persona_id, idem):
            return public_catalog(persona_shelf)
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
    persist_shelf(orch, persona_shelf)
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
    return public_catalog(persona_shelf)


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
    validate_shelf_name(shelf)
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
    persona_shelf = load_shelf(orch)
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
    prev_version = entry_version(existing)
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
    persist_shelf(orch, persona_shelf)
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
    return public_catalog(persona_shelf)


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
    validate_shelf_name(shelf)
    persona_shelf = load_shelf(orch)
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
    prev_version = entry_version(existing)
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
    persist_shelf(orch, persona_shelf)
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
    return public_catalog(persona_shelf)


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
    validate_shelf_name(shelf)
    persona_shelf = load_shelf(orch)
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
    prev_version = entry_version(existing)
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
    persist_shelf(orch, persona_shelf)
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
