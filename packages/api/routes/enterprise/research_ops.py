from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from api.export_peel import early_egress_export_json_miss
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import egress_json_openapi_responses, research_json_openapi_responses
from env.desktop_common import repo_root
from research.enterprise_index import (
    export_egress_audit_rows,
    list_enterprise_research_index,
    tenant_namespace,
)

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class ResearchIndexResponse(BaseModel):
    """GET /enterprise/research-index (`sak486-e`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    rows: list[dict[str, Any]] | None = None
    count: int | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class EgressAuditResponse(BaseModel):
    """GET /enterprise/egress-audit JSON (`sak486-e`)."""

    model_config = {"extra": "allow"}

    rows: list[dict[str, Any]] | None = None
    count: int | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/research-index",
    response_model=ResearchIndexResponse,
    response_model_exclude_none=True,
    summary="Enterprise research index (`sak486-e`)",
    responses=research_json_openapi_responses(),  # sak494-c
)
def enterprise_research_index(
    _gate: EnterpriseDep,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> dict[str, Any]:
    rows = list_enterprise_research_index(repo_root(), limit=limit)
    return {"tenant_id": tenant_namespace(), "rows": rows, "count": len(rows)}


@router.get(
    "/egress-audit",
    response_model=EgressAuditResponse,
    response_model_exclude_none=True,
    summary="Enterprise egress audit (`sak486-e`)",
    responses={
        200: {
            "content": {
                "application/json": {
                    "schema": EgressAuditResponse.model_json_schema(),
                },
                "application/x-ndjson": {},
            },
        },
        **egress_json_openapi_responses(),  # sak494-c
    },
)
def enterprise_egress_audit(
    _gate: EnterpriseDep,
    format: Annotated[str, Query(pattern="^(json|jsonl)$")] = "json",
) -> Response:
    if format == "json":
        if miss := early_egress_export_json_miss(feature="egress_audit"):  # sak494-e
            return miss
    rows = export_egress_audit_rows(repo_root())
    if format == "jsonl":
        import json

        body = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
        if body:
            body += "\n"
        return Response(content=body, media_type="application/x-ndjson")
    return JSONResponse({"rows": rows, "count": len(rows)})
