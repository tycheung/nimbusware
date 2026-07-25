"""Binary/HTML export peel guards (`sak488-e` / `sak490-f` / `sak496-g`).

OAuth redirect exports are out of scope — only JSON miss before streaming bodies.
OpenAPI 503 helpers live in ``api.schemas.peel_responses.export_openapi_responses``.
"""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from broker_client.dual_run_route import refuse_broker_only_http as _refuse_broker_only_http
from broker_client.flags import (
    broker_compute_enabled,
    broker_compute_only,
    broker_egress_enabled,
    broker_egress_only,
)
from broker_client.peel_assert import build_http_miss
from compute.broker_route import COMPUTE_ONLY_MSG

EGRESS_ONLY_MSG = (
    "Nimbusware enterprise egress audit export unavailable under "
    "NIMBUSWARE_BROKER_EGRESS=2; use SwissArmyNoife egress audit"
)


def export_miss_body(*, feature: str, error: str) -> dict[str, Any]:
    return build_http_miss(error, feature=feature)


def early_export_json_miss(*, feature: str, error: str | None = None) -> JSONResponse | None:
    if not broker_compute_enabled():
        return None
    msg = error or (
        f"{feature} export unavailable under NIMBUSWARE_BROKER_COMPUTE peel; "
        "broker export path required"
    )
    _refuse_broker_only_http(
        only=broker_compute_only,
        code="broker_compute_only",
        message=COMPUTE_ONLY_MSG,
    )
    return JSONResponse(content=export_miss_body(feature=feature, error=msg))


def early_egress_export_json_miss(*, feature: str, error: str | None = None) -> JSONResponse | None:
    if not broker_egress_enabled():
        return None
    msg = error or (
        f"{feature} export unavailable under NIMBUSWARE_BROKER_EGRESS peel; "
        "broker export path required"
    )
    _refuse_broker_only_http(
        only=broker_egress_only,
        code="broker_egress_only",
        message=EGRESS_ONLY_MSG,
    )
    body = export_miss_body(feature=feature, error=msg)
    body["status"] = "degraded"
    return JSONResponse(content=body)
