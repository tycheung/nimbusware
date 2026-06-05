from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import Response

from nimbusware_orchestrator.enterprise_audit_export import build_enterprise_audit_bundle_bytes
from nimbusware_api.deps import IamStoreDep, StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_env.desktop_common import repo_root

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


@router.get("/audit-export")
def enterprise_audit_export(
    _gate: EnterpriseDep,
    store: StoreDep,
    iam: IamStoreDep,
    since: Annotated[datetime | None, Query()] = None,
    until: Annotated[datetime | None, Query()] = None,
) -> Response:
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
