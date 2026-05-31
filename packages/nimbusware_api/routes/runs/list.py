"""GET /runs list handler."""

from __future__ import annotations

import binascii
import json
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import HTTPException, Query, Request, Response
from fastapi.routing import APIRouter

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.read_models import (
    _decode_run_list_cursor,
    _encode_run_list_cursor,
    _parse_query_datetime,
    _runs_list_query_string,
    _sanitize_workflow_profile_prefix,
)
from nimbusware_api.routes.runs.constants import INCLUDE_SUMMARY_MAX_LIMIT
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    RUN_LIST_LINK_HEADER,
)
from nimbusware_api.schemas.runs import RunListResponse, RunSummary
from nimbusware_projections.run_summary import RUN_LIST_FILTER_STATUSES, build_run_summary

router = APIRouter()

@router.get(
    "/runs",
    response_model=RunListResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Recent run identifiers",
            "headers": {
                "Link": RUN_LIST_LINK_HEADER,
            },
            "content": {
                "application/json": {
                    "example": {
                        "run_ids": ["11111111-1111-4111-8111-111111111111"],
                        "total": 1,
                        "has_more": False,
                        "order": "newest_first",
                        "limit": 50,
                        "offset": 0,
                        "include_summary": 0,
                    },
                    "examples": {
                        "keyset_page": {
                            "summary": (
                                "cursor + next_cursor (offset 0; Link rel=next uses cursor=)"
                            ),
                            "value": {
                                "run_ids": ["11111111-1111-4111-8111-111111111111"],
                                "total": 50,
                                "has_more": True,
                                "order": "newest_first",
                                "limit": 1,
                                "offset": 0,
                                "include_summary": 0,
                                "next_cursor": (
                                    "eyJzIjoxMjM0LCJyIjoiMTExMTExMTEtMTExMS00MTExLTgxMTEtMTExMTExMTExMTExIn0"
                                ),
                            },
                        },
                        "with_summaries": {
                            "summary": "include_summary=1 (limit capped at 20)",
                            "value": {
                                "run_ids": ["11111111-1111-4111-8111-111111111111"],
                                "total": 1,
                                "has_more": False,
                                "order": "newest_first",
                                "limit": 10,
                                "offset": 0,
                                "include_summary": 1,
                                "summaries": {
                                    "11111111-1111-4111-8111-111111111111": {
                                        "status": "created",
                                        "workflow_profile": "default",
                                        "event_count": 1,
                                        "latest_event_type": "run.created",
                                        "terminal_event_type": None,
                                        "findings_count": 0,
                                        "has_escalation": False,
                                        "run_created_metadata": {},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def list_runs(
    request: Request,
    response: Response,
    store: StoreDep,
    limit: Annotated[int, Query(ge=1, le=200, description="Page size")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset into newest-first list")] = 0,
    workflow_profile: Annotated[
        str | None,
        Query(description="Filter by first run.created workflow_profile (case-insensitive)"),
    ] = None,
    created_after: Annotated[
        str | None,
        Query(
            description="ISO-8601 lower bound on first run.created occurred_at (inclusive, UTC)",
        ),
    ] = None,
    created_before: Annotated[
        str | None,
        Query(
            description="ISO-8601 upper bound on first run.created occurred_at (inclusive, UTC)",
        ),
    ] = None,
    workflow_profile_prefix: Annotated[
        str | None,
        Query(
            description=(
                "When ``workflow_profile`` is unset: case-insensitive prefix on first "
                "run.created workflow_profile (alphanumeric, dot, dash, underscore; max 64)"
            ),
        ),
    ] = None,
    order: Annotated[
        Literal["newest_first", "oldest_first"],
        Query(description="Sort by last store activity per run"),
    ] = "newest_first",
    include_summary: Annotated[
        int,
        Query(
            ge=0,
            le=1,
            description=(
                "When ``1``, include ``summaries`` keyed by run_id (max ``limit`` "
                f"{INCLUDE_SUMMARY_MAX_LIMIT}; request 422 if larger)"
            ),
        ),
    ] = 0,
    has_escalation: Annotated[
        int | None,
        Query(
            ge=0,
            le=1,
            description="When ``1``, only runs with a ``run.escalated`` event; ``0`` only without",
        ),
    ] = None,
    cursor: Annotated[
        str | None,
        Query(
            description=(
                "Opaque keyset cursor (from ``next_cursor``). When set, ``offset`` must be ``0``; "
                "ordering uses max ``store_seq`` per run plus ``run_id`` tiebreaker (same as "
                "offset pagination)."
            ),
        ),
    ] = None,
    status: Annotated[
        str | None,
        Query(
            description=(
                "Filter by replay-derived run status (same strings as run summaries): "
                "``created``, ``running``, or ``terminal``."
            ),
        ),
    ] = None,
) -> RunListResponse:
    lim = min(max(limit, 1), 200)
    off = max(offset, 0)
    if include_summary == 1 and lim > INCLUDE_SUMMARY_MAX_LIMIT:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "include_summary_limit_exceeded",
                f"include_summary=1 requires limit<={INCLUDE_SUMMARY_MAX_LIMIT}",
                details={"limit": lim, "max": INCLUDE_SUMMARY_MAX_LIMIT},
            ),
        )
    try:
        ca = _parse_query_datetime("created_after", created_after)
        cb = _parse_query_datetime("created_before", created_before)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                str(exc),
                details={"field": "created_after_or_created_before"},
            ),
        ) from exc
    wpfx = _sanitize_workflow_profile_prefix(workflow_profile_prefix)
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
                details={"status": raw_list_status, "allowed": sorted(RUN_LIST_FILTER_STATUSES)},
            ),
        )
    list_status_filter: str | None = raw_list_status
    use_cursor = cursor is not None and str(cursor).strip() != ""
    if use_cursor and off != 0:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "cursor pagination cannot be combined with a non-zero offset",
                details={"offset": off},
            ),
        )
    cursor_seq: int | None = None
    cursor_rid: UUID | None = None
    if use_cursor:
        try:
            cs, cr = _decode_run_list_cursor(str(cursor).strip())
            cursor_seq = cs
            cursor_rid = cr
        except (
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
            binascii.Error,
            UnicodeDecodeError,
        ) as exc:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "invalid_cursor",
                    "cursor is not a valid keyset token",
                    details={"reason": str(exc)},
                ),
            ) from exc
    total = store.count_recent_runs(
        workflow_profile=workflow_profile,
        workflow_profile_prefix=wpfx,
        created_after=ca,
        created_before=cb,
        has_escalation=esc_filter,
        list_status=list_status_filter,
    )
    next_cursor_out: str | None = None
    if use_cursor and cursor_seq is not None and cursor_rid is not None:
        rows_page, page_has_more = store.list_recent_run_rows_cursor(
            limit=lim,
            cursor_after_seq=cursor_seq,
            cursor_after_run_id=cursor_rid,
            workflow_profile=workflow_profile,
            workflow_profile_prefix=wpfx,
            created_after=ca,
            created_before=cb,
            has_escalation=esc_filter,
            list_status=list_status_filter,
            order=order,
        )
        ids = [r[0] for r in rows_page]
        has_more = page_has_more
        off_out = 0
        if page_has_more and rows_page:
            last = rows_page[-1]
            next_cursor_out = _encode_run_list_cursor(last[1], last[0])
    else:
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
        has_more = off + len(ids) < total
        off_out = off
        if has_more and ids:
            mx_last = store.max_store_seq_for_run(str(ids[-1]))
            if mx_last is not None:
                next_cursor_out = _encode_run_list_cursor(mx_last, ids[-1])
    out: dict[str, Any] = {
        "run_ids": [str(x) for x in ids],
        "total": total,
        "has_more": has_more,
        "limit": lim,
        "offset": off_out,
        "order": order,
        "include_summary": include_summary,
    }
    if next_cursor_out is not None:
        out["next_cursor"] = next_cursor_out
    if workflow_profile is not None:
        out["workflow_profile"] = workflow_profile
    if wpfx is not None:
        out["workflow_profile_prefix"] = wpfx
    if created_after is not None:
        out["created_after"] = created_after
    if created_before is not None:
        out["created_before"] = created_before
    if has_escalation is not None:
        out["has_escalation"] = has_escalation
    if list_status_filter is not None:
        out["status"] = list_status_filter
    if include_summary == 1:
        summaries: dict[str, RunSummary] = {}
        for rid in ids:
            rows = store.list_run_events(str(rid))
            summaries[str(rid)] = RunSummary.model_validate(build_run_summary(rows))
        out["summaries"] = summaries
    has_more_bool = bool(out["has_more"])
    link_parts: list[str] = []
    if has_more_bool:
        if use_cursor:
            if next_cursor_out is not None:
                next_q = _runs_list_query_string(
                    limit=lim,
                    offset=None,
                    order=order,
                    include_summary=include_summary,
                    workflow_profile=workflow_profile,
                    workflow_profile_prefix=wpfx,
                    created_after=created_after,
                    created_before=created_before,
                    has_escalation=has_escalation,
                    cursor=next_cursor_out,
                    list_status=list_status_filter,
                )
                next_url = str(request.url.replace(query=next_q))
                link_parts.append(f'<{next_url}>; rel="next"')
        else:
            next_q = _runs_list_query_string(
                limit=lim,
                offset=off + len(ids),
                order=order,
                include_summary=include_summary,
                workflow_profile=workflow_profile,
                workflow_profile_prefix=wpfx,
                created_after=created_after,
                created_before=created_before,
                has_escalation=has_escalation,
                list_status=list_status_filter,
            )
            next_url = str(request.url.replace(query=next_q))
            link_parts.append(f'<{next_url}>; rel="next"')
    if not use_cursor and off > 0:
        prev_off = max(0, off - lim)
        prev_q = _runs_list_query_string(
            limit=lim,
            offset=prev_off,
            order=order,
            include_summary=include_summary,
            workflow_profile=workflow_profile,
            workflow_profile_prefix=wpfx,
            created_after=created_after,
            created_before=created_before,
            has_escalation=has_escalation,
            list_status=list_status_filter,
        )
        prev_url = str(request.url.replace(query=prev_q))
        link_parts.append(f'<{prev_url}>; rel="prev"')
    if link_parts:
        response.headers["Link"] = ", ".join(link_parts)
    return RunListResponse.model_validate(out)
