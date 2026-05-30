"""Runs HTTP routes — composed sub-routers under ``/v1/runs*``."""

from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.routes.runs.constants import INCLUDE_SUMMARY_MAX_LIMIT
from nimbusware_api.routes.runs.create import CreateRunBody, router as create_router
from nimbusware_api.routes.runs.detail import router as detail_router
from nimbusware_api.routes.runs.lifecycle import router as lifecycle_router
from nimbusware_api.routes.runs.list import router as list_router
from nimbusware_api.routes.runs.maker_approval import router as maker_approval_router
from nimbusware_api.routes.runs.maker_progress import router as maker_progress_router
from nimbusware_api.read_models import *  # noqa: F403
from nimbusware_api.read_models import __all__ as _read_model_exports

__all__ = [
    "build_runs_router",
    "router",
    "INCLUDE_SUMMARY_MAX_LIMIT",
    "CreateRunBody",
    "list_router",
    "create_router",
    "detail_router",
    "lifecycle_router",
    "maker_progress_router",
    "maker_approval_router",
    *_read_model_exports,
]


def build_runs_router() -> APIRouter:
    """Compose runs sub-routers without changing path prefixes."""
    composed = APIRouter(tags=["runs"])
    composed.include_router(list_router)
    composed.include_router(create_router)
    composed.include_router(detail_router)
    composed.include_router(lifecycle_router)
    composed.include_router(maker_progress_router)
    composed.include_router(maker_approval_router)
    return composed


router = build_runs_router()
