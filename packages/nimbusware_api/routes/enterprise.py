"""Enterprise-only API surface (Lane D). Stub until fo201+ implementations land."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_env.edition import (
    ENTERPRISE_FEATURES,
    FEATURE_EPICS,
    edition,
    is_enterprise,
)
from nimbusware_iam.constants import IMPLEMENTED_ENTERPRISE_FEATURES

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


def _require_enterprise() -> None:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_edition_required",
                "This route requires NIMBUSWARE_EDITION=enterprise",
                details={"edition": edition()},
            ),
        )


EnterpriseDep = Annotated[None, Depends(_require_enterprise)]


@router.get("/status")
def enterprise_status(_gate: EnterpriseDep) -> dict:
    """Lane D readiness map — features flip to implemented as fo201+ ship."""
    features = {
        name: {
            "status": (
                "enabled"
                if name in IMPLEMENTED_ENTERPRISE_FEATURES
                else "planned"
            ),
            "epic": FEATURE_EPICS.get(name, ""),
        }
        for name in sorted(ENTERPRISE_FEATURES)
    }
    return {
        "edition": edition(),
        "lane": "D",
        "bootstrap_epic": "fo200",
        "features": features,
        "message": (
            "Enterprise fo201–fo207 enabled (IAM, fleet memory, NOTIFY, object-store, "
            "Redis fleet worker, fleet Ollama SLI, enterprise console)."
        ),
    }


@router.get("/health")
def enterprise_health(_gate: EnterpriseDep, store: StoreDep) -> dict:
    """Minimal enterprise probe (store reachable)."""
    _ = store
    return {
        "ok": True,
        "edition": edition(),
        "iam": "enabled" if "iam" in IMPLEMENTED_ENTERPRISE_FEATURES else "planned",
    }
