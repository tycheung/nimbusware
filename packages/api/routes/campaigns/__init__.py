from __future__ import annotations

from fastapi import APIRouter

from api.routes.campaigns.backlog import router as backlog_router
from api.routes.campaigns.create import router as create_router
from api.routes.campaigns.lifecycle import router as lifecycle_router
from api.routes.campaigns.progress import router as progress_router

router = APIRouter()
router.include_router(create_router)
router.include_router(backlog_router)
router.include_router(lifecycle_router)
router.include_router(progress_router)

__all__ = ["router"]
