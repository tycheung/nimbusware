from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from api.deps import OrchDep
from api.errors import problem
from api.schemas.model_bindings import UserDefaultsBody
from api.user import UserDep
from config.model_bindings_store import (
    list_binding_role_catalog,
    load_user_defaults,
    merge_role_bindings,
    save_user_defaults,
)
from config.store import PostgresConfigStore
from env.env_flags import nimbusware_database_url
from orchestrator.provider_registry import load_provider_presets
from orchestrator.routing.preflight import build_binding_preflight_report

router = APIRouter(tags=["platform"])


def _config_store() -> PostgresConfigStore | None:
    url = nimbusware_database_url()
    if not url:
        return None
    return PostgresConfigStore(url)


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


@router.get("/platform/model-bindings/defaults")
def get_model_binding_defaults(orch: OrchDep, _: UserDep) -> dict[str, Any]:
    store = _config_store()
    doc = load_user_defaults(orch.repo_root, store=store)
    return {
        "defaults": doc,
        "roles": merge_role_bindings(orch.repo_root, store=store),
        "providers": load_provider_presets(orch.repo_root),
    }


@router.put("/platform/model-bindings/defaults")
def put_model_binding_defaults(
    body: UserDefaultsBody,
    orch: OrchDep,
    _: UserDep,
) -> dict[str, Any]:
    store = _config_store()
    try:
        doc = save_user_defaults(
            orch.repo_root,
            body.model_dump(mode="json"),
            store=store,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_binding_defaults", str(exc)),
        ) from exc
    return {"defaults": doc}


@router.get("/platform/model-bindings/roles")
def get_model_binding_roles(orch: OrchDep, _: UserDep) -> dict[str, Any]:
    return {"roles": list_binding_role_catalog(orch.repo_root)}
