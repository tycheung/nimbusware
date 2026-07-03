from __future__ import annotations

from fastapi import APIRouter

from api.routes.runs.autopilot import router as autopilot_router
from api.routes.runs.compact import router as compact_router
from api.routes.runs.compactions import router as compactions_router
from api.routes.runs.constants import INCLUDE_SUMMARY_MAX_LIMIT
from api.routes.runs.context_artifacts import router as context_artifacts_router
from api.routes.runs.context_budget import router as context_budget_router
from api.routes.runs.create import CreateRunBody
from api.routes.runs.create import router as create_router
from api.routes.runs.detail import router as detail_router
from api.routes.runs.dev_env import router as dev_env_router
from api.routes.runs.enforcement import router as enforcement_router
from api.routes.runs.factory_evidence import router as factory_evidence_router
from api.routes.runs.interjection import router as interjection_router
from api.routes.runs.learnings import router as learnings_router
from api.routes.runs.lifecycle import router as lifecycle_router
from api.routes.runs.list import router as list_router
from api.routes.runs.list_helpers import (
    _parse_query_datetime,
    _runs_list_query_string,
    _sanitize_workflow_profile_prefix,
)
from api.routes.runs.maker_approval import router as maker_approval_router
from api.routes.runs.maker_progress import router as maker_progress_router
from api.routes.runs.memory_insert import router as memory_insert_router
from api.routes.runs.model_bindings_swap import router as model_bindings_swap_router
from api.routes.runs.replay_from import router as replay_from_router
from api.routes.runs.research import router as research_router
from api.routes.runs.slices import router as slices_router
from api.routes.runs.stitch_summary import router as stitch_summary_router
from api.routes.runs.stream import router as stream_router
from api.routes.runs.theater import router as theater_router
from api.routes.runs.timeline_explain import router as timeline_explain_router
from api.run_list_cursor import decode_run_list_cursor, encode_run_list_cursor
from projections.builders import *  # noqa: F403
from projections.builders import __all__ as _projection_exports

_decode_run_list_cursor = decode_run_list_cursor
_encode_run_list_cursor = encode_run_list_cursor

# Single source of truth for sub-router registration order (facade tests pin this tuple).
RUNS_SUB_ROUTER_NAMES: tuple[str, ...] = (
    "list_router",
    "create_router",
    "detail_router",
    "lifecycle_router",
    "model_bindings_swap_router",
    "maker_progress_router",
    "factory_evidence_router",
    "dev_env_router",
    "interjection_router",
    "autopilot_router",
    "enforcement_router",
    "learnings_router",
    "context_budget_router",
    "compact_router",
    "compactions_router",
    "replay_from_router",
    "context_artifacts_router",
    "memory_insert_router",
    "maker_approval_router",
    "research_router",
    "stream_router",
    "theater_router",
    "stitch_summary_router",
    "slices_router",
    "timeline_explain_router",
)

__all__ = [
    "build_runs_router",
    "router",
    "RUNS_SUB_ROUTER_NAMES",
    "INCLUDE_SUMMARY_MAX_LIMIT",
    "CreateRunBody",
    *RUNS_SUB_ROUTER_NAMES,
    *_projection_exports,
    "_decode_run_list_cursor",
    "_encode_run_list_cursor",
    "_parse_query_datetime",
    "_runs_list_query_string",
    "_sanitize_workflow_profile_prefix",
]


def build_runs_router() -> APIRouter:
    """Compose runs HTTP surface from sub-routers under ``api.routes.runs.*``."""
    composed = APIRouter(tags=["runs"])
    for name in RUNS_SUB_ROUTER_NAMES:
        composed.include_router(globals()[name])
    return composed


router = build_runs_router()
