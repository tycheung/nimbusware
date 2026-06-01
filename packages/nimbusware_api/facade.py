"""HTTP API v1 router facade — single entry for mounting under ``/v1``."""

from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.routes import (
    actions,
    bundles,
    custom_agents,
    ollama,
    personas,
    platform,
    preflight,
    projects,
    runs,
    scraper_artifacts,
)
from nimbusware_api.routes.enterprise import build_enterprise_router


def build_v1_router() -> APIRouter:
    """Compose all v1 route modules without changing individual path prefixes."""
    router = APIRouter()
    router.include_router(runs.router)
    router.include_router(actions.router)
    router.include_router(bundles.router)
    router.include_router(personas.router)
    router.include_router(custom_agents.router)
    router.include_router(projects.router)
    router.include_router(preflight.router)
    router.include_router(scraper_artifacts.router)
    router.include_router(platform.router)
    router.include_router(ollama.router)
    router.include_router(build_enterprise_router())
    return router
