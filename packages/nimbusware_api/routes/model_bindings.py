from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from nimbusware_api.deps import OrchDep
from nimbusware_api.user import UserDep
from nimbusware_orchestrator.binding_preflight import build_binding_preflight_report

router = APIRouter(tags=["platform"])


@router.get("/platform/model-bindings/preflight")
def get_model_bindings_preflight(
    orch: OrchDep,
    _: UserDep,
    workflow_profile: Annotated[str | None, Query()] = None,
    work_type: Annotated[str | None, Query()] = None,
    probe: Annotated[bool, Query()] = True,
) -> dict[str, Any]:
    mat = getattr(orch, "_config_materializer", None)
    return build_binding_preflight_report(
        orch.repo_root,
        workflow_profile=workflow_profile,
        work_type=work_type,
        materializer=mat,
        probe=probe,
    )
