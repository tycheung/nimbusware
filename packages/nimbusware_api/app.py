from __future__ import annotations

from nimbusware_env import load_dotenv
from nimbusware_env.edition import edition, is_enterprise

load_dotenv()

import logging
import os
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from nimbusware_api.errors import problem
from nimbusware_api.facade import build_v1_router
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_422, PROBLEM_RESPONSE_500
from nimbusware_config import ConfigMaterializer
from hermes_extensions.bundle_memory_factory import build_bundle_outcome_store
from hermes_memory.factory import build_memory_chunk_store
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.registry_db import load_registry_from_postgres
from hermes_orchestrator.run_dispatch import get_run_queue, run_dispatch_enabled
from hermes_store.memory import InMemoryEventStore
from hermes_store.postgres import PostgresEventStore
from nimbusware_iam.middleware import enterprise_iam_middleware
from nimbusware_iam.store import PostgresIamStore, build_iam_store
from nimbusware_maker.store import build_project_store

logger = logging.getLogger(__name__)

_OPENAPI_APP_DESCRIPTION = (
    "Nimbusware Hermes agent run orchestration HTTP API. "
    "Resource paths are under /v1. "
    "Operations are tagged **user** (Maker product loop) or **admin** (Admin Console / "
    "control plane). Individual edition: user routes are open locally; admin routes "
    "require ``X-Nimbusware-Admin-Token``. Enterprise: user routes need "
    "``X-Nimbusware-Api-Key`` with ``maker_user`` scope; admin routes need "
    "``maker_admin`` scope or the admin token (bootstrap). "
    "See PLAN_GAP.md Lane U for the full split."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    base, _ = default_paths(repo)
    url = os.environ.get("NIMBUSWARE_DATABASE_URL")
    roles_from_db = os.environ.get("NIMBUSWARE_ROLES_FROM_DB", "").lower() in ("1", "true", "yes")
    use_db_config = (
        os.environ.get("NIMBUSWARE_CONFIG_FROM_DB", "").strip().lower() in ("1", "true", "yes")
        and os.environ.get("NIMBUSWARE_CONFIG_FROM_FILES", "").strip().lower()
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
    app.state.iam_store = build_iam_store(url)
    app.state.project_store = build_project_store(url)
    if url and isinstance(app.state.iam_store, PostgresIamStore):
        app.state.iam_store.ensure_default_tenant()
    app.state.config_materializer = materializer
    notify_stop: threading.Event | None = None
    notify_thread: threading.Thread | None = None
    if materializer is not None and url:
        from nimbusware_config import (
            config_notify_listener_enabled,
            get_config_notify_hub,
            start_config_notify_listener,
        )

        if config_notify_listener_enabled():
            hub = get_config_notify_hub()
            hub.register(materializer)
            notify_stop = threading.Event()
            notify_thread = start_config_notify_listener(url, hub, notify_stop)
            app.state.config_notify_hub = hub
    app.state.orchestrator = RunOrchestrator(
        app.state.store,
        registry,
        repo_root=repo,
        base_config_path=base,
        config_materializer=materializer,
        memory_chunk_store=build_memory_chunk_store(url),
        bundle_outcome_store=build_bundle_outcome_store(url),
    )
    if run_dispatch_enabled():
        app.state.run_queue = get_run_queue()
    else:
        app.state.run_queue = None
    app.state.edition = edition()
    logger.info("Nimbusware edition=%s enterprise=%s", app.state.edition, is_enterprise())
    try:
        yield
    finally:
        if notify_stop is not None:
            notify_stop.set()
        if notify_thread is not None:
            notify_thread.join(timeout=5.0)
        if materializer is not None:
            hub = getattr(app.state, "config_notify_hub", None)
            if hub is not None:
                hub.unregister(materializer)


app = FastAPI(
    title="Nimbusware (Hermes agent)",
    version="0.5.0",
    description=_OPENAPI_APP_DESCRIPTION,
    lifespan=lifespan,
    responses={422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
    openapi_tags=[
        {
            "name": "user",
            "description": (
                "Maker product routes. Individual: implicit local user. Enterprise: "
                "``maker_user`` API key scope."
            ),
        },
        {
            "name": "admin",
            "description": (
                "Admin Console / control plane. Individual: ``X-Nimbusware-Admin-Token``. "
                "Enterprise: ``maker_admin`` scope or admin token."
            ),
        },
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
            "name": "platform",
            "description": "Product edition, local readiness, and feature gates.",
        },
        {
            "name": "projects",
            "description": (
                "Project workspaces bound to Hermes runs. "
                "``GET/POST`` are user routes; ``DELETE`` is admin-only."
            ),
        },
        {
            "name": "enterprise",
            "description": (
                "Enterprise edition routes (404 when NIMBUSWARE_EDITION=individual). "
                "IAM routes require X-Nimbusware-Api-Key on Enterprise."
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


@app.middleware("http")
async def _request_logging_middleware(request: Request, call_next):
    import time

    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    logging.getLogger("nimbusware_api.request").info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.middleware("http")
async def _enterprise_iam(request: Request, call_next):
    return await enterprise_iam_middleware(request, call_next)


app.include_router(build_v1_router(), prefix="/v1")


def _build_openapi_schema() -> dict:
    from fastapi.openapi.utils import get_openapi

    from nimbusware_api.openapi_access import enrich_openapi_access_tags

    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    enrich_openapi_access_tags(schema)
    return schema


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    app.openapi_schema = _build_openapi_schema()
    return app.openapi_schema


app.openapi = custom_openapi
