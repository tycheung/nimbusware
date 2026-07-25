from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from api.schemas.openapi import PROBLEM_RESPONSE_503


class DeleteOkResponse(BaseModel):
    """DELETE peel JSON body (`sak488-d`)."""

    model_config = {"extra": "allow"}

    ok: bool = True
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class ExportErrorResponse(BaseModel):
    """Binary/HTML export peel miss (`sak488-e`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


class TheaterExportMissResponse(ExportErrorResponse):
    """GET /runs/{run_id}/theater/export peel miss (`sak489-e`)."""

    pass


class SseStreamErrorResponse(BaseModel):
    """SSE ``event: error`` peel envelope (`sak489-f`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    feature: str | None = None
    error: str | None = None
    status: str | None = None


class ComputePeelMissResponse(BaseModel):
    """COMPUTE peel miss base for /v1/compute/* and session compute routes (`sak491-c`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


class ComputeNodeListMissResponse(ComputePeelMissResponse):
    """GET /compute/nodes COMPUTE=1 peel miss (`sak491-c`)."""

    nodes: list[dict[str, Any]] = Field(default_factory=list)


class WorkUnitClaimMissResponse(ComputePeelMissResponse):
    """POST /compute/work-units/claim COMPUTE=1 peel miss (`sak491-c`)."""

    work_unit: dict[str, Any] | None = None


class WorkUnitQueueDepthMissResponse(ComputePeelMissResponse):
    """GET /compute/work-units/queue COMPUTE=1 peel miss (`sak491-c`)."""

    queued: int = 0
    session_id: str | None = None


class SessionComputeStatusMissResponse(ComputePeelMissResponse):
    """GET /sessions/{session_id}/compute/status COMPUTE=1 peel miss (`sak491-c`)."""

    session_id: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    queue_depth: int = 0


class FleetMeshStatusMissResponse(ComputePeelMissResponse):
    """GET /enterprise/fleet-mesh/status COMPUTE=1 peel miss (`sak492-b`)."""

    session_id: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    queue_depth: int = 0


def compute_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for COMPUTE JSON routes: 503 broker-only (`sak491-c` / artifact `sak492-c` / `sak493-c`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak492-c / sak493-c: mirrored in packages/admin_ui/src/api/openapi.json


def export_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI 503 for COMPUTE-gated binary/HTML export routes (`sak496-g`)."""
    return compute_json_openapi_responses(not_found=not_found)


class CapacityPeelMissResponse(BaseModel):
    """CAPACITY peel miss base for /v1/platform/* hardware + model routes (`sak492-a`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None
    capacity_source: str | None = None


class PlatformReadinessPeelMissResponse(CapacityPeelMissResponse):
    """GET /platform/readiness CAPACITY peel miss (`sak493-a`)."""

    checks: dict[str, Any] = Field(default_factory=dict)


def capacity_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for CAPACITY JSON routes: 503 broker-only (`sak492-a` / artifact `sak492-c` / `sak493-c`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak492-c / sak493-c: mirrored in packages/admin_ui/src/api/openapi.json


class LlmPeelMissResponse(BaseModel):
    """LLM peel miss base for /v1/chat/classify and LLM JSON routes (`sak493-b`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


class IntentClassifierMissResponse(LlmPeelMissResponse):
    """POST /chat/classify LLM=1 peel miss (`sak493-b`)."""

    classification: dict[str, Any] = Field(default_factory=dict)


def llm_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for LLM JSON routes: 503 broker-only (`sak493-b` / artifact `sak493-c`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak493-c / sak497-e / sak499-c: mirrored in packages/admin_ui/src/api/openapi.json


class MemoryPeelMissResponse(BaseModel):
    """MEMORY peel miss base for /v1/enterprise/fleet-memory/* routes (`sak493-i`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


class FleetMemoryStatusMissResponse(MemoryPeelMissResponse):
    """GET /enterprise/fleet-memory/status MEMORY=1 peel miss (`sak493-i`)."""

    tenant_id: str | None = None
    org_scope_hash: str | None = None
    fleet_memory_enabled: bool | None = None
    local_generation_id: str | None = None
    local_chunk_count: int = 0
    remote: dict[str, Any] | None = None


class FleetMemorySearchMissResponse(MemoryPeelMissResponse):
    """GET /enterprise/fleet-memory/search MEMORY=1 peel miss (`sak493-i`)."""

    org_scope_hash: str | None = None
    query: str | None = None
    embedding_mode: str | None = None
    hit_count: int = 0
    hits: list[dict[str, Any]] = Field(default_factory=list)
    excerpt: str | None = None


class MemoryChunksMissResponse(MemoryPeelMissResponse):
    """GET /memory/chunks MEMORY=1 peel miss (`sak498-b`)."""

    project_id: str | None = None
    repo_scope_hash: str | None = None
    workspace_path: str | None = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class MemoryChunkInsertMissResponse(MemoryPeelMissResponse):
    """POST /runs/{run_id}/memory-chunks/{chunk_id}/insert MEMORY=1 peel miss (`sak498-b`)."""

    run_id: str | None = None
    chunk_id: str | None = None


# sak498-e: context-artifacts MEMORY-gated long-tail OpenAPI miss shapes


class ContextArtifactFromCompactionMissResponse(MemoryPeelMissResponse):
    """POST /runs/{run_id}/context-artifacts/from-compaction MEMORY peel miss (`sak498-e`)."""

    run_id: str | None = None
    project_id: str | None = None
    artifact_id: str | None = None
    title: str | None = None
    kind: str | None = None


class ContextArtifactInsertMissResponse(MemoryPeelMissResponse):
    """POST /runs/{run_id}/context-artifacts/{artifact_id}/insert MEMORY peel miss (`sak498-e`)."""

    run_id: str | None = None
    artifact_id: str | None = None
    title: str | None = None
    kind: str | None = None


class ContextArtifactBridgeMissResponse(MemoryPeelMissResponse):
    """POST /projects/{project_id}/context-artifacts/{artifact_id}/bridge-memory MEMORY peel miss (`sak499-c`)."""

    project_id: str | None = None
    artifact_id: str | None = None
    bridge_path: str | None = None
    indexed: bool = False


class LaunchEvalMissResponse(LlmPeelMissResponse):
    """POST /runs/{run_id}/maker/launch-eval LLM peel miss (`sak499-c`)."""

    pass


def memory_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for MEMORY JSON routes: 503 broker-only (`sak493-i` / `sak494-c` / `sak498-b` / `sak498-e` / `sak499-c`)."""
    return enterprise_peel_json_openapi_responses(not_found=not_found)


def enterprise_peel_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """Shared OpenAPI 503 for enterprise peel JSON routes (`sak494-c` / `sak496-e`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak494-c / sak496-e: mirrored in packages/admin_ui/src/api/openapi.json


def research_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for RESEARCH JSON routes: 503 broker-only (`sak494-c`)."""
    return enterprise_peel_json_openapi_responses(not_found=not_found)


def egress_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for EGRESS JSON routes: 503 broker-only (`sak494-c`)."""
    return enterprise_peel_json_openapi_responses(not_found=not_found)


def admin_bff_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for admin BFF peel JSON routes (`sak494-g` / `sak496-f`)."""
    return enterprise_peel_json_openapi_responses(not_found=not_found)


def runs_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for runs/maker JSON routes: 503 broker-only (`sak496-f`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak496-f: mirrored in packages/admin_ui/src/api/openapi.json


class LongTailPeelMissResponse(BaseModel):
    """Long-tail peel miss base for admin OAuth, subscription OAuth, bundle catalog (`sak495-d`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


class AdminOAuthSessionMissResponse(LongTailPeelMissResponse):
    """GET /admin/oauth/session peel miss (`sak495-d`)."""

    authenticated: bool | None = None
    console_role: str | None = None


class AdminOAuthLogoutMissResponse(LongTailPeelMissResponse):
    """POST /admin/oauth/logout peel miss (`sak495-d`)."""

    ok: bool | None = None


class SubscriptionOauthStatusMissResponse(LongTailPeelMissResponse):
    """GET /platform/provider-subscriptions/oauth/status peel miss (`sak495-d`)."""

    providers: list[dict[str, Any]] = Field(default_factory=list)
    callback_path: str | None = None
    mock_mode: bool = False


class CatalogCandidatesMissResponse(LongTailPeelMissResponse):
    """GET /bundles/catalog-candidates peel miss (`sak495-d`)."""

    candidates: list[dict[str, Any]] = Field(default_factory=list)


class BundleCatalogSourceMissResponse(LongTailPeelMissResponse):
    """GET /bundles/catalog/source peel miss (`sak495-d`)."""

    authoritative: str | None = None
    document: str | None = None
    namespace: str | None = None
    document_key: str | None = None
    path: str | None = None


def long_tail_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
    unauthorized: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for long-tail peel JSON routes (`sak495-d` / artifact `sak495-d`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    if unauthorized is not None:
        responses[401] = unauthorized
    return responses  # sak495-d: mirrored in packages/admin_ui/src/api/openapi.json


def with_long_tail_peel_503(
    responses: dict[int | str, dict[str, Any]] | None = None,
    *,
    not_found: dict[str, Any] | None = None,
    unauthorized: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    out: dict[int | str, dict[str, Any]] = dict(responses or {})
    out.update(
        long_tail_json_openapi_responses(
            not_found=not_found,
            unauthorized=unauthorized,
        ),
    )
    return out


def with_enterprise_peel_503(
    responses: dict[int | str, dict[str, Any]] | None = None,
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    out: dict[int | str, dict[str, Any]] = dict(responses or {})
    out.update(enterprise_peel_json_openapi_responses(not_found=not_found))
    return out


def artifact_peel_503_response() -> dict[str, Any]:
    """JSON-ready 503 Problem body for ``openapi.json`` peel mirrors (`sak504-d`)."""
    import copy

    return copy.deepcopy(PROBLEM_RESPONSE_503)


def ensure_operation_peel_503(operation: dict[str, Any]) -> bool:
    """Insert artifact peel 503 into an OpenAPI operation if missing (`sak505-d`).

    Returns True when a 503 response was added.
    """
    responses = operation.setdefault("responses", {})
    if "503" in responses:
        return False
    responses["503"] = artifact_peel_503_response()
    return True


def ensure_paths_peel_503(
    openapi_paths: dict[str, Any],
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> int:
    """Batch-insert artifact peel 503 for ``(path, method)`` pairs (`sak506-d`).

    Skips targets whose path/method is absent (`sak518-d`).
    Returns count of operations that newly received a 503 response.
    """
    added = 0
    for path, method in targets:
        path_item = openapi_paths.get(path)
        if not isinstance(path_item, dict):
            continue
        op = path_item.get(method)
        if not isinstance(op, dict):
            continue
        if ensure_operation_peel_503(op):
            added += 1
    return added


def count_missing_peel_503(
    openapi_paths: dict[str, Any],
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> int:
    """Count target operations still missing peel 503 (`sak507-d` / DRY `sak509-d`)."""
    return len(list_missing_peel_503(openapi_paths, targets))


def list_missing_peel_503(
    openapi_paths: dict[str, Any],
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for path, method in targets:
        op = openapi_paths.get(path, {}).get(method)
        if op is None or "503" not in op.get("responses", {}):
            out.append((path, method))
    return out


def patch_openapi_json_peel_503(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> int:
    """Load ``openapi.json``, ensure peel 503 on targets, write back (`sak510-d`).

    Returns count of operations that newly received a 503 response.
    """
    import json
    from pathlib import Path

    path = Path(openapi_json_path)
    spec = json.loads(path.read_text(encoding="utf-8"))
    added = ensure_paths_peel_503(spec["paths"], targets)
    path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return added


def list_missing_peel_503_in_openapi_json(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> list[tuple[str, str]]:
    import json
    from pathlib import Path

    path = Path(openapi_json_path)
    spec = json.loads(path.read_text(encoding="utf-8"))
    return list_missing_peel_503(spec["paths"], targets)


def count_missing_peel_503_in_openapi_json(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> int:
    """Count targets still missing peel 503 in ``openapi.json`` (`sak516-d`)."""
    return len(list_missing_peel_503_in_openapi_json(openapi_json_path, targets))


def openapi_peel_503_complete(
    openapi_paths: dict[str, Any],
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> bool:
    complete, _missing = peel_503_coverage(openapi_paths, targets)
    return complete


def peel_503_coverage(
    openapi_paths: dict[str, Any],
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> tuple[bool, list[tuple[str, str]]]:
    missing = list_missing_peel_503(openapi_paths, targets)
    return (not missing, missing)


def openapi_peel_503_complete_in_file(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> bool:
    """True when ``openapi.json`` already documents peel 503 for all targets.

    ``sak513-d``; DRY via ``count_missing_peel_503_in_openapi_json`` (`sak519-d`).
    """
    return count_missing_peel_503_in_openapi_json(openapi_json_path, targets) == 0


def peel_503_coverage_in_file(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> tuple[bool, list[tuple[str, str]]]:
    missing = list_missing_peel_503_in_openapi_json(openapi_json_path, targets)
    return (not missing, missing)


def ensure_openapi_json_peel_503(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> tuple[int, list[tuple[str, str]]]:
    """Patch peel 503 onto targets; return ``(added, remaining_missing)`` (`sak517-d`)."""
    added = patch_openapi_json_peel_503(openapi_json_path, targets)
    missing = list_missing_peel_503_in_openapi_json(openapi_json_path, targets)
    return added, missing


def openapi_json_peel_503_report(
    openapi_json_path: Any,
    targets: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    """Return ``{complete, missing, count}`` for peel 503 targets in file (`sak520-d`).

    DRY via ``peel_503_coverage_in_file`` (`sak521-d`).
    """
    complete, missing = peel_503_coverage_in_file(openapi_json_path, targets)
    return {
        "complete": complete,
        "missing": missing,
        "count": len(missing),
    }


# OAuth mock / browser redirect surfaces are not peel product paths (`sak521-b`).
PEEL_503_OAUTH_SKIP: frozenset[tuple[str, str]] = frozenset(
    {
        ("/v1/platform/provider-subscriptions/oauth/mock-authorize", "get"),
        ("/v1/admin/oauth/login", "get"),
        ("/v1/admin/oauth/mock-authorize", "get"),
        ("/v1/admin/oauth/callback", "get"),
    },
)


def iter_openapi_json_operations(
    openapi_json_path: Any,
) -> list[tuple[str, str]]:
    import json
    from pathlib import Path

    path = Path(openapi_json_path)
    spec = json.loads(path.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    for op_path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            if "responses" not in op:
                continue
            out.append((op_path, method))
    return out


def list_missing_product_peel_503_in_openapi_json(
    openapi_json_path: Any,
    *,
    skip: frozenset[tuple[str, str]] | set[tuple[str, str]] | None = None,
) -> list[tuple[str, str]]:
    skip_set = PEEL_503_OAUTH_SKIP if skip is None else frozenset(skip)
    targets = [t for t in iter_openapi_json_operations(openapi_json_path) if t not in skip_set]
    return list_missing_peel_503_in_openapi_json(openapi_json_path, targets)


def openapi_product_peel_503_complete_in_file(
    openapi_json_path: Any,
    *,
    skip: frozenset[tuple[str, str]] | set[tuple[str, str]] | None = None,
) -> bool:
    return not list_missing_product_peel_503_in_openapi_json(
        openapi_json_path,
        skip=skip,
    )


def platform_peel_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """Shared OpenAPI 503 for platform peel JSON routes (`sak495-c`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak495-c: mirrored in packages/admin_ui/src/api/openapi.json


def analytics_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for platform analytics JSON routes: 503 broker-only (`sak495-c`)."""
    return platform_peel_json_openapi_responses(not_found=not_found)


def platform_bootstrap_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for playwright-bootstrap routes: 503 broker-only (`sak495-c`)."""
    return platform_peel_json_openapi_responses(not_found=not_found)


def campaign_json_openapi_responses(
    *,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI for /v1/campaigns* JSON routes: 503 broker-only (`sak497-d`)."""
    responses: dict[int | str, dict[str, Any]] = {
        503: PROBLEM_RESPONSE_503,
    }
    if not_found is not None:
        responses[404] = not_found
    return responses  # sak497-d: mirrored in packages/admin_ui/src/api/openapi.json
