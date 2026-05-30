"""Enterprise route package — aggregates sub-routers under ``/v1/enterprise/*``."""

from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.routes.enterprise.config_notify import router as config_notify_router
from nimbusware_api.routes.enterprise.core import EnterpriseDep, router as core_router
from nimbusware_api.routes.enterprise.fleet_memory import router as fleet_memory_router
from nimbusware_api.routes.enterprise.fleet_ollama_sli import router as fleet_ollama_sli_router
from nimbusware_api.routes.enterprise.fleet_worker import router as fleet_worker_router
from nimbusware_api.routes.enterprise.iam import router as iam_router
from nimbusware_api.routes.enterprise.object_store import router as object_store_router

__all__ = [
    "EnterpriseDep",
    "build_enterprise_router",
    "core_router",
    "iam_router",
    "fleet_memory_router",
    "config_notify_router",
    "object_store_router",
    "fleet_worker_router",
    "fleet_ollama_sli_router",
]


def build_enterprise_router() -> APIRouter:
    """Single router mounting all enterprise sub-routers (paths unchanged)."""
    router = APIRouter()
    router.include_router(core_router)
    router.include_router(iam_router)
    router.include_router(fleet_memory_router)
    router.include_router(config_notify_router)
    router.include_router(object_store_router)
    router.include_router(fleet_worker_router)
    router.include_router(fleet_ollama_sli_router)
    return router
