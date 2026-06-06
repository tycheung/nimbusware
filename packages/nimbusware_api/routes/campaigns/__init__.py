from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.routes.campaigns.create import router as create_router

router = APIRouter()
router.include_router(create_router)

__all__ = ["router"]
