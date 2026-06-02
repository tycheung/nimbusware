from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from hermes_orchestrator.ollama_manage import (
    OllamaManageError,
    delete_model,
    filter_models,
    list_installed_models,
    ollama_reachable,
    pull_model,
    runtime_base_url_from_routing,
)
from hermes_orchestrator.ollama_pull_jobs import get_pull_job, start_pull_job
from hermes_orchestrator.ollama_user_policy import (
    assert_user_may,
    merge_policy_into_routing,
    policy_from_routing,
)
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.ollama import (
    OllamaDeleteResponse,
    OllamaModelEntry,
    OllamaModelsResponse,
    OllamaPrimaryRoutingRequest,
    OllamaPullJobStatusResponse,
    OllamaPullRequest,
    OllamaPullResponse,
    OllamaUserPolicyBody,
)
from nimbusware_config.keys import KEY_MODEL_ROUTING, NS_POLICY
from nimbusware_config.persist import load_model_routing_dict, persist_model_routing_dict

router = APIRouter(tags=["platform", "ollama"])


def _routing_models(routing: dict[str, Any]) -> tuple[str | None, list[str]]:
    models = routing.get("models")
    if not isinstance(models, dict):
        return None, []
    primary_raw = models.get("primary")
    primary_id: str | None = None
    if isinstance(primary_raw, dict):
        pid = primary_raw.get("id")
        if isinstance(pid, str) and pid.strip():
            primary_id = pid.strip()
    fallbacks: list[str] = []
    for item in models.get("fallbacks") or []:
        if isinstance(item, dict):
            fid = item.get("id")
            if isinstance(fid, str) and fid.strip():
                fallbacks.append(fid.strip())
    return primary_id, fallbacks


def _materializer(orch: OrchDep) -> Any | None:
    return getattr(orch, "_config_materializer", None)


def _load_routing(orch: OrchDep) -> dict[str, Any]:
    mat = _materializer(orch)
    return load_model_routing_dict(orch.repo_root, materializer=mat)


def _publish_routing_notify() -> None:
    try:
        from nimbusware_config.flags import config_notify_enabled
        from nimbusware_config.notify import get_config_notify_hub

        if config_notify_enabled():
            get_config_notify_hub().publish_local(
                namespace=NS_POLICY,
                document_key=KEY_MODEL_ROUTING,
                version=1,
            )
    except ImportError:
        return


def _save_routing(orch: OrchDep, routing: dict[str, Any]) -> None:
    mat = _materializer(orch)
    persist_model_routing_dict(orch.repo_root, routing, materializer=mat)
    if mat is None or not getattr(mat, "use_db", False):
        _publish_routing_notify()


def _models_response(
    orch: OrchDep,
    *,
    query: str | None = None,
) -> OllamaModelsResponse:
    routing = _load_routing(orch)
    base = runtime_base_url_from_routing(routing)
    reachable = ollama_reachable(base)
    rows = list_installed_models(base)
    if query:
        rows = filter_models(rows, query)
    primary_id, fallbacks = _routing_models(routing)
    policy = policy_from_routing(routing)
    return OllamaModelsResponse(
        reachable=reachable,
        base_url=base,
        primary_model_id=primary_id,
        fallback_model_ids=fallbacks,
        user_policy=OllamaUserPolicyBody(
            allow_pull=policy.allow_pull,
            allow_delete=policy.allow_delete,
            allow_update_routing=policy.allow_update_routing,
            updated_at=None,
        ),
        models=[OllamaModelEntry(**row.to_dict()) for row in rows],
        query=query or None,
    )


@router.get("/platform/ollama/models", response_model=OllamaModelsResponse)
def get_ollama_models(
    orch: OrchDep,
    q: Annotated[str | None, Query(description="Filter installed model names")] = None,
) -> OllamaModelsResponse:
    return _models_response(orch, query=q)


def _policy_forbidden(action: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=problem(
            "forbidden",
            f"Ollama {action} is disabled for Maker users (ollama_user_policy)",
            details={"action": action},
        ),
    )


@router.post("/platform/ollama/pull", response_model=OllamaPullResponse)
def post_ollama_pull(body: OllamaPullRequest, orch: OrchDep) -> OllamaPullResponse:
    routing = _load_routing(orch)
    policy = policy_from_routing(routing)
    try:
        assert_user_may(policy, "pull")
    except PermissionError:
        raise _policy_forbidden("pull") from None
    base = runtime_base_url_from_routing(routing)
    job = start_pull_job(model=body.model.strip(), host=base)
    return OllamaPullResponse(model=body.model.strip(), status="accepted", job_id=job.job_id)


@router.get("/platform/ollama/pull/{job_id}", response_model=OllamaPullJobStatusResponse)
def get_ollama_pull_job(job_id: str) -> OllamaPullJobStatusResponse:
    job = get_pull_job(job_id.strip())
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "pull_job_not_found", "Unknown Ollama pull job", details={"job_id": job_id}
            ),
        )
    return OllamaPullJobStatusResponse(
        job_id=job.job_id,
        model=job.model,
        status=job.status,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


@router.delete("/platform/ollama/models/{model_name}", response_model=OllamaDeleteResponse)
def delete_ollama_model(model_name: str, orch: OrchDep) -> OllamaDeleteResponse:
    routing = _load_routing(orch)
    policy = policy_from_routing(routing)
    try:
        assert_user_may(policy, "delete")
    except PermissionError:
        raise _policy_forbidden("delete") from None
    base = runtime_base_url_from_routing(routing)
    try:
        delete_model(model_name, host=base)
    except OllamaManageError as exc:
        raise HTTPException(
            status_code=502,
            detail=problem("ollama_delete_failed", str(exc)),
        ) from exc
    return OllamaDeleteResponse(model=model_name.strip())


@router.patch("/platform/ollama/routing/primary", response_model=OllamaModelsResponse)
def patch_primary_routing(
    body: OllamaPrimaryRoutingRequest,
    orch: OrchDep,
) -> OllamaModelsResponse:
    routing = _load_routing(orch)
    policy = policy_from_routing(routing)
    try:
        assert_user_may(policy, "update_routing")
    except PermissionError:
        raise _policy_forbidden("update_routing") from None
    models = routing.get("models")
    if not isinstance(models, dict):
        models = {}
        routing["models"] = models
    primary = models.get("primary")
    if not isinstance(primary, dict):
        primary = {}
    primary["id"] = body.primary_model_id.strip()
    models["primary"] = primary
    _save_routing(orch, routing)
    return _models_response(orch)


@router.patch("/admin/ollama/user-policy", response_model=OllamaUserPolicyBody)
def patch_ollama_user_policy(
    body: OllamaUserPolicyBody,
    orch: OrchDep,
    _admin: AdminDep,
) -> OllamaUserPolicyBody:
    routing = _load_routing(orch)
    merged = merge_policy_into_routing(
        routing,
        allow_pull=body.allow_pull,
        allow_delete=body.allow_delete,
        allow_update_routing=body.allow_update_routing,
    )
    _save_routing(orch, merged)
    policy_doc = merged.get("ollama_user_policy")
    body_kwargs = (
        dict(policy_doc) if isinstance(policy_doc, dict) else policy_from_routing(merged).to_dict()
    )
    return OllamaUserPolicyBody(**body_kwargs)


@router.post("/admin/ollama/pull", response_model=OllamaPullResponse)
def admin_post_ollama_pull(
    body: OllamaPullRequest,
    orch: OrchDep,
    _admin: AdminDep,
) -> OllamaPullResponse:
    routing = _load_routing(orch)
    base = runtime_base_url_from_routing(routing)
    try:
        pull_model(body.model, host=base)
    except OllamaManageError as exc:
        raise HTTPException(
            status_code=502,
            detail=problem("ollama_pull_failed", str(exc)),
        ) from exc
    return OllamaPullResponse(model=body.model.strip())


@router.delete("/admin/ollama/models/{model_name}", response_model=OllamaDeleteResponse)
def admin_delete_ollama_model(
    model_name: str,
    orch: OrchDep,
    _admin: AdminDep,
) -> OllamaDeleteResponse:
    routing = _load_routing(orch)
    base = runtime_base_url_from_routing(routing)
    try:
        delete_model(model_name, host=base)
    except OllamaManageError as exc:
        raise HTTPException(
            status_code=502,
            detail=problem("ollama_delete_failed", str(exc)),
        ) from exc
    return OllamaDeleteResponse(model=model_name.strip())
