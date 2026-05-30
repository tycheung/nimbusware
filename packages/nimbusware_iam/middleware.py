"""Enterprise IAM request middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.responses import JSONResponse

from nimbusware_api.errors import problem
from nimbusware_env.edition import is_enterprise
from nimbusware_iam.constants import API_KEY_HEADER
from nimbusware_iam.context import reset_auth_context, set_auth_context


def _is_iam_exempt(path: str) -> bool:
    if path in {"/openapi.json", "/docs", "/redoc"}:
        return True
    if path == "/v1/platform/edition":
        return True
    if path == "/v1/platform/readiness":
        return True
    if path == "/v1/enterprise/iam/bootstrap":
        return True
    return False


async def enterprise_iam_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not is_enterprise():
        reset_auth_context()
        return await call_next(request)

    if _is_iam_exempt(request.url.path):
        reset_auth_context()
        return await call_next(request)

    iam_store = getattr(request.app.state, "iam_store", None)
    if iam_store is None:
        return JSONResponse(
            status_code=503,
            content=problem(
                "iam_not_configured",
                "Enterprise IAM store is not configured",
            ),
            media_type="application/problem+json",
        )

    api_key = request.headers.get(API_KEY_HEADER, "").strip()
    if not api_key:
        return JSONResponse(
            status_code=401,
            content=problem(
                "api_key_required",
                f"Enterprise edition requires {API_KEY_HEADER}",
            ),
            media_type="application/problem+json",
        )

    ctx = iam_store.verify_api_key(api_key)
    if ctx is None:
        return JSONResponse(
            status_code=401,
            content=problem("invalid_api_key", "missing or invalid API key"),
            media_type="application/problem+json",
        )

    set_auth_context(ctx)
    try:
        return await call_next(request)
    finally:
        reset_auth_context()
