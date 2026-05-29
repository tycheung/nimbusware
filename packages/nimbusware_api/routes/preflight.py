"""Fleet preflight history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.preflight_read_model import preflight_timeline_summary
from nimbusware_api.routes import runs as runs_routes
from nimbusware_api.schemas.openapi import (
    PREFLIGHT_HISTORY_RESPONSE_200,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_api.schemas.preflight import (
    PreflightHistoryEntry,
    PreflightHistoryResponse,
    PreflightMetricsExport,
    PreflightMetricsExportFilters,
)
from hermes_store.protocol import serialized_event_from_row

router = APIRouter(tags=["preflight"])

PREFLIGHT_HISTORY_MAX_LIMIT = 50
RUN_LIST_FILTER_STATUSES = frozenset({"created", "running", "terminal"})


@router.get(
    "/preflight-history",
    response_model=PreflightHistoryResponse,
    responses={
        200: PREFLIGHT_HISTORY_RESPONSE_200,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def get_preflight_history(
    store: StoreDep,
    limit: Annotated[
        int,
        Query(ge=1, le=PREFLIGHT_HISTORY_MAX_LIMIT, description="Max runs to scan"),
    ] = 10,
    offset: Annotated[int, Query(ge=0, description="Offset into ordered run list")] = 0,
    workflow_profile: Annotated[
        str | None,
        Query(description="Filter by first run.created workflow_profile (case-insensitive)"),
    ] = None,
    created_after: Annotated[
        str | None,
        Query(description="ISO-8601 lower bound on first run.created occurred_at (UTC)"),
    ] = None,
    created_before: Annotated[
        str | None,
        Query(description="ISO-8601 upper bound on first run.created occurred_at (UTC)"),
    ] = None,
    workflow_profile_prefix: Annotated[
        str | None,
        Query(description="Case-insensitive prefix on workflow_profile when exact filter unset"),
    ] = None,
    order: Annotated[
        Literal["newest_first", "oldest_first"],
        Query(description="Sort by last store activity per run"),
    ] = "newest_first",
    has_escalation: Annotated[
        int | None,
        Query(ge=0, le=1, description="``1`` only escalated runs; ``0`` only without"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Replay-derived status: ``created``, ``running``, ``terminal``"),
    ] = None,
    include_metrics_export: Annotated[
        int,
        Query(
            ge=0,
            le=1,
            description=(
                "``1`` attaches ``metrics_export`` with ``export_schema_version`` and "
                "``export_window_consistent`` for external scrapers; ``0`` omits it"
            ),
        ),
    ] = 0,
) -> PreflightHistoryResponse:
    """Bounded fleet preflight aggregation (O(limit) store reads per request).

    For each recent ``run_id``, replays events and applies the same
    ``preflight_timeline_summary`` projection as ``GET /v1/runs/{id}/timeline``.
    """
    lim = min(max(limit, 1), PREFLIGHT_HISTORY_MAX_LIMIT)
    off = max(offset, 0)
    try:
        ca = runs_routes._parse_query_datetime("created_after", created_after)
        cb = runs_routes._parse_query_datetime("created_before", created_before)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                str(exc),
                details={"field": "created_after_or_created_before"},
            ),
        ) from exc
    wpfx = runs_routes._sanitize_workflow_profile_prefix(workflow_profile_prefix)
    if workflow_profile is not None and workflow_profile_prefix is not None:
        wpfx = None
    esc_filter: bool | None = None if has_escalation is None else bool(has_escalation)
    raw_list_status = str(status).strip() if status is not None and str(status).strip() else None
    if raw_list_status is not None and raw_list_status not in RUN_LIST_FILTER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "status must be one of: created, running, terminal",
                details={
                    "status": raw_list_status,
                    "allowed": sorted(RUN_LIST_FILTER_STATUSES),
                },
            ),
        )
    list_status_filter: str | None = raw_list_status
    total = store.count_recent_runs(
        workflow_profile=workflow_profile,
        workflow_profile_prefix=wpfx,
        created_after=ca,
        created_before=cb,
        has_escalation=esc_filter,
        list_status=list_status_filter,
    )
    ids = store.list_recent_run_ids(
        limit=lim,
        offset=off,
        workflow_profile=workflow_profile,
        workflow_profile_prefix=wpfx,
        created_after=ca,
        created_before=cb,
        has_escalation=esc_filter,
        list_status=list_status_filter,
        order=order,
    )
    entries: list[PreflightHistoryEntry] = []
    runs_with_preflight = 0
    runs_with_p95_latency = 0
    runs_with_multisample_preflight = 0
    runs_with_checks_passed = 0
    validated_model_ids: set[str] = set()
    p95_total = 0
    max_p95_latency_ms: int | None = None
    row_map: dict[str, list[dict[str, object]]]
    if hasattr(store, "list_run_events_many"):
        row_map = store.list_run_events_many([str(x) for x in ids])
    else:
        row_map = {str(x): store.list_run_events(str(x)) for x in ids}
    for run_id in ids:
        rid = str(run_id)
        rows = row_map.get(rid, [])
        events = [serialized_event_from_row(r) for r in rows]
        pf = preflight_timeline_summary(events) if events else None
        if pf is not None:
            runs_with_preflight += 1
            checks_passed = pf.get("checks_passed")
            if isinstance(checks_passed, list) and any(
                isinstance(item, str) and item.strip() for item in checks_passed
            ):
                runs_with_checks_passed += 1
            validated_model_id = pf.get("validated_model_id")
            if isinstance(validated_model_id, str) and validated_model_id.strip():
                validated_model_ids.add(validated_model_id.strip())
            samples = pf.get("health_latency_samples_ms")
            if isinstance(samples, list) and len(samples) > 1:
                runs_with_multisample_preflight += 1
            p95 = pf.get("p95_latency_ms")
            if isinstance(p95, int) and not isinstance(p95, bool) and p95 >= 0:
                runs_with_p95_latency += 1
                p95_total += p95
                if max_p95_latency_ms is None or p95 > max_p95_latency_ms:
                    max_p95_latency_ms = p95
        entries.append(PreflightHistoryEntry(run_id=rid, preflight=pf))
    has_more = off + len(ids) < total
    runs_without_preflight = len(ids) - runs_with_preflight
    coverage: float | None = None
    if ids:
        coverage = runs_with_preflight / len(ids)
    avg_p95_latency_ms: float | None = None
    if runs_with_p95_latency > 0:
        avg_p95_latency_ms = p95_total / runs_with_p95_latency
    p95_coverage: float | None = None
    if runs_with_preflight > 0:
        p95_coverage = runs_with_p95_latency / runs_with_preflight
    metrics_export: PreflightMetricsExport | None = None
    if include_metrics_export == 1:
        metrics_export = PreflightMetricsExport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            export_schema_version=1,
            window_limit=lim,
            window_offset=off,
            order=order,
            window_total_matching_runs=total,
            runs_scanned=len(ids),
            has_more=has_more,
            runs_with_preflight=runs_with_preflight,
            runs_without_preflight=runs_without_preflight,
            runs_with_p95_latency=runs_with_p95_latency,
            runs_with_multisample_preflight=runs_with_multisample_preflight,
            runs_with_checks_passed=runs_with_checks_passed,
            distinct_validated_model_id_count=len(validated_model_ids),
            avg_p95_latency_ms=avg_p95_latency_ms,
            max_p95_latency_ms=max_p95_latency_ms,
            preflight_coverage_ratio=coverage,
            p95_latency_coverage_ratio=p95_coverage,
            export_window_consistent=(len(ids) == len(entries)),
            filters=PreflightMetricsExportFilters(
                workflow_profile=workflow_profile,
                workflow_profile_prefix=wpfx,
                created_after=ca.isoformat() if ca is not None else None,
                created_before=cb.isoformat() if cb is not None else None,
                has_escalation=esc_filter,
                status=list_status_filter,
            ),
        )
    return PreflightHistoryResponse(
        entries=entries,
        limit=lim,
        total=total,
        has_more=has_more,
        order=order,
        runs_with_preflight=runs_with_preflight,
        runs_without_preflight=runs_without_preflight,
        runs_with_p95_latency=runs_with_p95_latency,
        avg_p95_latency_ms=avg_p95_latency_ms,
        max_p95_latency_ms=max_p95_latency_ms,
        preflight_coverage_ratio=coverage,
        p95_latency_coverage_ratio=p95_coverage,
        runs_with_multisample_preflight=runs_with_multisample_preflight,
        runs_with_checks_passed=runs_with_checks_passed,
        distinct_validated_model_id_count=len(validated_model_ids),
        metrics_export=metrics_export,
    )
