from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.read_models import *  # noqa: F403
from nimbusware_api.read_models import __all__ as _read_model_exports
from nimbusware_api.routes.runs.compact import router as compact_router
from nimbusware_api.routes.runs.compactions import router as compactions_router
from nimbusware_api.routes.runs.constants import INCLUDE_SUMMARY_MAX_LIMIT
from nimbusware_api.routes.runs.context_artifacts import router as context_artifacts_router
from nimbusware_api.routes.runs.context_budget import router as context_budget_router
from nimbusware_api.routes.runs.create import CreateRunBody
from nimbusware_api.routes.runs.create import router as create_router
from nimbusware_api.routes.runs.detail import router as detail_router
from nimbusware_api.routes.runs.factory_evidence import router as factory_evidence_router
from nimbusware_api.routes.runs.lifecycle import router as lifecycle_router
from nimbusware_api.routes.runs.list import router as list_router
from nimbusware_api.routes.runs.maker_approval import router as maker_approval_router
from nimbusware_api.routes.runs.maker_progress import router as maker_progress_router
from nimbusware_api.routes.runs.replay_from import router as replay_from_router
from nimbusware_api.routes.runs.research import router as research_router
from nimbusware_api.routes.runs.slices import router as slices_router
from nimbusware_api.routes.runs.stitch_summary import router as stitch_summary_router
from nimbusware_api.routes.runs.stream import router as stream_router
from nimbusware_api.routes.runs.theater import router as theater_router
from nimbusware_api.routes.runs.timeline_explain import router as timeline_explain_router

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
    "context_budget_router",
    "compact_router",
    "compactions_router",
    "replay_from_router",
    "context_artifacts_router",
    "maker_approval_router",
    "research_router",
    "stream_router",
    "theater_router",
    *_read_model_exports,
]


def build_runs_router() -> APIRouter:
    composed = APIRouter(tags=["runs"])
    composed.include_router(list_router)
    composed.include_router(create_router)
    composed.include_router(detail_router)
    composed.include_router(lifecycle_router)
    composed.include_router(maker_progress_router)
    composed.include_router(factory_evidence_router)
    composed.include_router(context_budget_router)
    composed.include_router(compact_router)
    composed.include_router(compactions_router)
    composed.include_router(replay_from_router)
    composed.include_router(context_artifacts_router)
    composed.include_router(maker_approval_router)
    composed.include_router(research_router)
    composed.include_router(stream_router)
    composed.include_router(theater_router)
    composed.include_router(stitch_summary_router)
    composed.include_router(slices_router)
    composed.include_router(timeline_explain_router)
    return composed


router = build_runs_router()
