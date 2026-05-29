from __future__ import annotations

from hermes_env import load_dotenv

load_dotenv()

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from hermes_api.errors import problem
from hermes_api.routes import actions, bundles, personas, preflight, runs, scraper_artifacts
from hermes_api.schemas.openapi import PROBLEM_RESPONSE_422, PROBLEM_RESPONSE_500
from hermes_config import ConfigMaterializer
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.registry_db import load_registry_from_postgres
from hermes_orchestrator.run_dispatch import get_run_queue, run_dispatch_enabled
from hermes_store.memory import InMemoryEventStore
from hermes_store.postgres import PostgresEventStore

logger = logging.getLogger(__name__)

_OPENAPI_APP_DESCRIPTION = (
    "Nimbusware Hermes agent run orchestration HTTP API. "
    "Resource paths are under /v1. "
    "Admin routes (for example POST /v1/roles/{role_id}/execute) require "
    "HERMES_ADMIN_TOKEN. See PLAN_GAP.md at the repository root for scope. "
    "OpenAPI documents optional RFC 5988 Link headers on several GET 200 responses "
    "where the server may emit them."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    repo = Path(os.environ.get("HERMES_REPO_ROOT", ".")).resolve()
    base, _ = default_paths(repo)
    url = os.environ.get("HERMES_DATABASE_URL")
    roles_from_db = os.environ.get("HERMES_ROLES_FROM_DB", "").lower() in ("1", "true", "yes")
    use_db_config = (
        os.environ.get("HERMES_CONFIG_FROM_DB", "").strip().lower() in ("1", "true", "yes")
        and os.environ.get("HERMES_CONFIG_FROM_FILES", "").strip().lower()
        not in ("1", "true", "yes")
    )
    materializer: ConfigMaterializer | None = None
    if use_db_config and url:
        materializer = ConfigMaterializer(repo, use_db=True)
    if url and roles_from_db:
        registry = load_registry_from_postgres(url)
    else:
        registry = RoleRegistry.from_yaml(repo / "configs" / "roles.yaml")
    if url:
        app.state.store = PostgresEventStore(url)
    else:
        app.state.store = InMemoryEventStore()
    app.state.config_materializer = materializer
    app.state.orchestrator = RunOrchestrator(
        app.state.store,
        registry,
        repo_root=repo,
        base_config_path=base,
        config_materializer=materializer,
    )
    if run_dispatch_enabled():
        app.state.run_queue = get_run_queue()
    else:
        app.state.run_queue = None
    yield


app = FastAPI(
    title="Nimbusware (Hermes agent)",
    version="0.5.0",
    description=_OPENAPI_APP_DESCRIPTION,
    lifespan=lifespan,
    responses={422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
    openapi_tags=[
        {
            "name": "runs",
            "description": (
                "Run list (pagination, filters, keyset), detail, timeline, findings, "
                "and lifecycle transitions."
            ),
        },
        {
            "name": "actions",
            "description": "Run-scoped actions (retry, escalate) and admin role execute stub.",
        },
        {
            "name": "bundles",
            "description": (
                "Read-only bundle catalog helpers: ``GET /v1/bundles/search`` performs "
                "bounded vector search (``k`` capped by server defaults) under the frozen "
                "repo root; each **200** response includes ``faiss_index_ready`` (and related "
                "index hints) when the optional FAISS index is present."
            ),
        },
        {
            "name": "personas",
            "description": (
                "Read-only persona shelf catalog (``configs/personas/shelves.yaml``)."
            ),
        },
        {
            "name": "preflight",
            "description": (
                "Fleet preflight history (``GET /v1/preflight-history``) — bounded "
                "aggregation over recent runs without per-run timeline fan-out."
            ),
        },
        {
            "name": "scraper-artifacts",
            "description": (
                "Read-only on-disk scraper artifact inventory under the configured "
                "cache directory."
            ),
        },
    ],
)


@app.exception_handler(HTTPException)
async def hermes_http_exception_handler(
    _request: Request,
    exc: HTTPException,
) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            media_type="application/problem+json",
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "http_error", "message": str(exc.detail)},
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def hermes_validation_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=problem(
            "validation_error",
            "request validation failed",
            details={"errors": exc.errors()},
        ),
        media_type="application/problem+json",
    )


@app.exception_handler(Exception)
async def hermes_uncaught_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=problem("internal_error", "an internal server error occurred"),
        media_type="application/problem+json",
    )


app.include_router(runs.router, prefix="/v1")
app.include_router(actions.router, prefix="/v1")
app.include_router(bundles.router, prefix="/v1")
app.include_router(personas.router, prefix="/v1")
app.include_router(preflight.router, prefix="/v1")
app.include_router(scraper_artifacts.router, prefix="/v1")
