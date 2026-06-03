from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_env.edition import edition_manifest, enterprise_compose_profiles
from nimbusware_hw.cache import get_cached_profile, rescan_hardware
from nimbusware_hw.fit import rank_models
from nimbusware_hw.governor import governor_for_profile
from nimbusware_maker.readiness import build_platform_readiness

router = APIRouter(tags=["platform"])


class HardwareRescanBody(BaseModel):
    emit_event: bool = Field(
        default=False,
        description="Reserved: append hardware.profile.detected when platform ops events ship",
    )


@router.get("/platform/edition")
def get_platform_edition() -> dict:
    body = edition_manifest()
    body["compose_profiles"] = enterprise_compose_profiles()
    return body


@router.get("/platform/readiness")
def get_platform_readiness(orch: OrchDep, store: StoreDep) -> dict:
    return build_platform_readiness(repo_root=orch.repo_root, store=store)


@router.get("/platform/hardware")
def get_platform_hardware(orch: OrchDep) -> dict:
    profile = get_cached_profile()
    governor = governor_for_profile(profile)
    ranked = rank_models(orch.repo_root, profile, limit=20)
    return {
        "profile": profile.model_dump_public(),
        "resource_governor": governor.to_metadata(),
        "models_ranked": ranked[:20],
    }


@router.post("/platform/hardware/rescan")
def post_platform_hardware_rescan(
    orch: OrchDep,
    _store: StoreDep,
    body: HardwareRescanBody | None = None,
) -> dict:
    del body
    profile = rescan_hardware()
    governor = governor_for_profile(profile)
    ranked = rank_models(orch.repo_root, profile, limit=20)
    return {
        "profile": profile.model_dump_public(),
        "resource_governor": governor.to_metadata(),
        "models_ranked": ranked[:20],
    }
