from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from api.deps import IamStoreDep, StoreDep
from api.export_peel import early_export_json_miss
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import ExportErrorResponse, enterprise_peel_json_openapi_responses
from env.desktop_common import repo_root
from orchestrator.replay.export import build_enterprise_audit_bundle_bytes

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class EnterpriseAuditExportErrorResponse(ExportErrorResponse):
    """GET /enterprise/audit-export peel miss (`sak488-e`).

    OAuth redirect exports are out of scope for this slice.
    """

    pass


@router.get(
    "/audit-export",
    response_model=None,
    responses={
        200: {
            "content": {
                "application/gzip": {},
                "application/json": {"model": EnterpriseAuditExportErrorResponse},
            },
        },
        **enterprise_peel_json_openapi_responses(),  # sak496-e
    },
)
def enterprise_audit_export(
    _gate: EnterpriseDep,
    store: StoreDep,
    iam: IamStoreDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
):
    if miss := early_export_json_miss(feature="enterprise_audit_export"):
        return miss
    payload = build_enterprise_audit_bundle_bytes(
        iam_store=iam,
        event_store=store,
        repo_root=repo_root(),
        since=since,
        until=until,
    )
    return Response(
        content=payload,
        media_type="application/gzip",
        headers={"Content-Disposition": 'attachment; filename="enterprise-audit.tar.gz"'},
    )
