"""Platform metadata routes (available on all editions)."""

from __future__ import annotations

from fastapi import APIRouter

from nimbusware_env.edition import edition_manifest, enterprise_compose_profiles

router = APIRouter(tags=["platform"])


@router.get("/platform/edition")
def get_platform_edition() -> dict:
    """Current product edition and enterprise feature gate manifest."""
    body = edition_manifest()
    body["compose_profiles"] = enterprise_compose_profiles()
    return body
