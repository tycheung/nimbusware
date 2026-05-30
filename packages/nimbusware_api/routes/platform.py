"""Platform metadata routes (available on all editions)."""

from __future__ import annotations

from fastapi import APIRouter

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_env.edition import edition_manifest, enterprise_compose_profiles
from nimbusware_maker.readiness import build_platform_readiness

router = APIRouter(tags=["platform"])


@router.get("/platform/edition")
def get_platform_edition() -> dict:
    """Current product edition and enterprise feature gate manifest."""
    body = edition_manifest()
    body["compose_profiles"] = enterprise_compose_profiles()
    return body


@router.get("/platform/readiness")
def get_platform_readiness(orch: OrchDep, store: StoreDep) -> dict:
    """Local readiness for maker UX — Ollama, database, disk, config (fo307)."""
    return build_platform_readiness(repo_root=orch.repo_root, store=store)

