from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from hermes_research.enterprise_index import (
    export_egress_audit_rows,
    list_enterprise_research_index,
    tenant_namespace,
)
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_env.desktop_common import repo_root

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


@router.get("/research-index")
def enterprise_research_index(
    _gate: EnterpriseDep,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> dict[str, Any]:
    rows = list_enterprise_research_index(repo_root(), limit=limit)
    return {"tenant_id": tenant_namespace(), "rows": rows, "count": len(rows)}


@router.get("/egress-audit")
def enterprise_egress_audit(
    _gate: EnterpriseDep,
    format: Annotated[str, Query(pattern="^(json|jsonl)$")] = "json",
) -> Response:
    rows = export_egress_audit_rows(repo_root())
    if format == "jsonl":
        import json

        body = "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
        if body:
            body += "\n"
        return Response(content=body, media_type="application/x-ndjson")
    return JSONResponse({"rows": rows, "count": len(rows)})
