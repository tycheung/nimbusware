from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from agent_core.models import serialize_event_persistent, validate_event_dict
from api.admin import AdminDep
from api.deps import IamStoreDep, OrchDep, StoreDep
from api.errors import problem
from api.routes.admin_ui_timeline import (
    TimelinePanelsResponse,
    build_timeline_panels_payload,
    timeline_events_from_store,
)
from api.routes.personas_helpers import load_shelf
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import admin_bff_json_openapi_responses
from console import enterprise_console as ent_console
from console.critic_matrix_display import critic_matrix_rows_from_events
from console.critic_reliability_display import (
    critic_reliability_caption,
    critic_reliability_summary_from_events,
    critic_reliability_table_rows,
    fleet_critic_reliability_caption,
    fleet_critic_reliability_table_rows,
)
from console.findings_display import findings_list_from_response, findings_table_rows
from console.operator_chat_core import ChatState, process_user_message
from console.services import enterprise as enterprise_svc
from console.workflow_explainers.integration_adapter_writer import (
    integration_adapter_writer_from_events,
    integration_adapter_writer_run_caption,
    integration_adapter_writer_run_table_rows,
)
from env.edition import is_enterprise
from extensions.persona_scope_overlap import persona_scope_overlap_report
from iam.constants import API_KEY_HEADER
from orchestrator.fleet.analytics import compare_tenant_metrics
from orchestrator.fleet.policies import (
    FleetAutopilotPolicy,
    FleetEnforcementPolicy,
    load_fleet_autopilot_policies,
    load_fleet_enforcement_policies,
    save_fleet_autopilot_policies,
    save_fleet_enforcement_policies,
    tenant_autopilot_policy,
    tenant_enforcement_policy,
)
from orchestrator.profiles.autopilot_profiles import CHECKPOINT_CATALOG
from store.protocol import serialized_event_from_row

router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])

_chat_sessions: dict[str, ChatState] = {}


class OperatorChatMessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class OperatorChatMessageResponse(BaseModel):
    reply: str
    last_run_id: str = ""
    classification: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None
    status: str | None = None


class FleetDashboardResponse(BaseModel):
    """GET /admin/ui/enterprise/fleet-dashboard (`sak480-e`)."""

    model_config = {"extra": "allow"}

    memory_rows: list[Any] = Field(default_factory=list)
    worker_caption: str | None = None
    sli_caption: str | None = None
    hardware_rows: list[Any] = Field(default_factory=list)
    export_json: Any = None
    export_filename_slug: str | None = None
    fleet_memory: dict[str, Any] | None = None
    preflight_aggregate: dict[str, Any] | None = None
    fleet_worker: dict[str, Any] | None = None
    hardware_fleet: dict[str, Any] | None = None
    critic_reliability: dict[str, Any] | None = None
    critic_reliability_caption: str | None = None
    critic_reliability_rows: list[Any] | None = None
    archetype_fit_rows: list[Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None
    capacity_source: str | None = None
    status: str | None = None


@router.post(
    "/operator-chat/message",
    response_model=OperatorChatMessageResponse,
    response_model_exclude_none=True,
    summary="Operator chat message (`sak491-h`; peel-aware `sak494-g`)",
    responses=admin_bff_json_openapi_responses(),
)
def operator_chat_message(
    body: OperatorChatMessageBody,
    _admin: AdminDep,
    x_nimbusware_chat_session: str | None = Header(default=None),
) -> OperatorChatMessageResponse:
    key = (x_nimbusware_chat_session or "default").strip()[:128] or "default"
    state = _chat_sessions.setdefault(key, ChatState())
    reply = process_user_message(body.text, state)
    miss = state.last_peel_miss
    return OperatorChatMessageResponse(
        reply=reply,
        last_run_id=state.last_run_id,
        classification=state.last_classification,
        via=miss.get("via") if miss else None,
        error=miss.get("error") if miss else None,
        feature=miss.get("feature") if miss else None,
        status=miss.get("status") if miss else None,
    )


class AdminProjectionResponse(BaseModel):
    """OpenAPI payload (`sak481-e` / `sak481-f`)."""

    model_config = {"extra": "allow"}

    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/runs/{run_id}/findings-table",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    responses=admin_bff_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f
    summary="Findings table (`sak481-f`)",
)
def findings_table(run_id: UUID, store: StoreDep, _admin: AdminDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    findings_raw: list[dict[str, Any]] = []
    for r in rows:
        if r["event_type"] != "finding.created":
            continue
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        findings_raw.append(serialize_event_persistent(ev))
    body = {"run_id": str(run_id), "findings": findings_raw}
    listed = findings_list_from_response(body)
    return {"run_id": str(run_id), "rows": findings_table_rows(listed)}


@router.get(
    "/runs/{run_id}/critic-matrix-table",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    responses=admin_bff_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f
    summary="Critic matrix (`sak481-f`)",
)
def critic_matrix_table(run_id: UUID, store: StoreDep, _admin: AdminDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    events: list[dict[str, Any]] = []
    for r in rows:
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        events.append(serialize_event_persistent(ev))
    return {"run_id": str(run_id), "rows": critic_matrix_rows_from_events(events)}


@router.get(
    "/runs/{run_id}/integration-adapter-writer",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    responses=admin_bff_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f
    summary="Integration adapter writer (`sak482-f`)",
)
def integration_adapter_writer_run(
    run_id: UUID,
    store: StoreDep,
    _admin: AdminDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    iaw = integration_adapter_writer_from_events(rows)
    return {
        "run_id": str(run_id),
        "present": iaw is not None,
        "caption": integration_adapter_writer_run_caption(iaw),
        "rows": integration_adapter_writer_run_table_rows(iaw),
        "metadata": iaw or {},
    }


@router.get(
    "/runs/{run_id}/critic-reliability",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    responses=admin_bff_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f
    summary="Critic reliability table (`sak482-f`)",
)
def critic_reliability_table(run_id: UUID, store: StoreDep, _admin: AdminDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    summary = critic_reliability_summary_from_events(rows)
    return {
        "run_id": str(run_id),
        "caption": critic_reliability_caption(summary),
        "rows": critic_reliability_table_rows(summary),
        "summary": summary,
    }


def _resolve_tenant_uuid(iam: Any, tenant_ref: str) -> str:
    ref = tenant_ref.strip()
    if not ref:
        return ""
    try:
        return str(UUID(ref))
    except ValueError:
        pass
    for tenant in iam.list_tenants():
        if tenant.slug == ref:
            return str(tenant.tenant_id)
    return ref


def _require_enterprise_api_key(
    x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
) -> str:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_edition_required",
                "Fleet dashboard requires NIMBUSWARE_EDITION=enterprise",
            ),
        )
    key = (x_api_key or "").strip()
    if not key:
        raise HTTPException(
            status_code=401,
            detail=problem(
                "api_key_required",
                f"Enterprise fleet dashboard requires {API_KEY_HEADER}",
            ),
        )
    return key


@router.get(
    "/enterprise/fleet-dashboard",
    response_model=FleetDashboardResponse,
    response_model_exclude_none=True,
    summary="Enterprise fleet dashboard BFF (`sak480-e`; peel-aware `sak494-g`)",
    responses=admin_bff_json_openapi_responses(),
)
def enterprise_fleet_dashboard(
    _admin: AdminDep,
    iam: IamStoreDep,
    api_key: Annotated[str, Depends(_require_enterprise_api_key)],
    tenant_id: Annotated[str | None, Query()] = None,
    preflight_limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    memory = enterprise_svc.fetch_fleet_memory_status(api_key=api_key)
    preflight = enterprise_svc.fetch_fleet_preflight_aggregate(
        api_key=api_key,
        limit=preflight_limit,
    )
    worker = enterprise_svc.fetch_fleet_worker_health(api_key=api_key)
    hardware = enterprise_svc.fetch_platform_hardware_fleet()
    critic: dict[str, Any] | None = None
    critic_caption: str | None = None
    critic_rows: list[dict[str, str]] = []
    tid_ref = (tenant_id or "").strip()
    tid_uuid = _resolve_tenant_uuid(iam, tid_ref) if tid_ref else ""
    if tid_uuid:
        critic = enterprise_svc.fetch_fleet_critic_reliability(
            api_key=api_key,
            tenant_id=tid_uuid,
        )
        critic_caption = fleet_critic_reliability_caption(critic)
        critic_rows = fleet_critic_reliability_table_rows(critic)
    peel = enterprise_svc.first_peel_from_fetches(
        memory,
        preflight,
        worker,
        hardware,
        critic,
    )
    return {
        **peel,
        "memory_rows": ent_console.fleet_memory_status_table_rows(memory),
        "worker_caption": ent_console.fleet_worker_health_caption(worker),
        "sli_caption": ent_console.fleet_sli_aggregate_caption(preflight),
        "hardware_rows": ent_console.fleet_hardware_tier_table_rows(hardware),
        "export_json": ent_console.fleet_dashboard_export_json(
            memory=memory,
            preflight_aggregate=preflight,
            worker=worker,
        ),
        "export_filename_slug": ent_console.fleet_dashboard_export_filename_slug(),
        "fleet_memory": memory,
        "preflight_aggregate": preflight,
        "fleet_worker": worker,
        "hardware_fleet": hardware,
        "critic_reliability": critic,
        "critic_reliability_caption": critic_caption,
        "critic_reliability_rows": critic_rows,
        "archetype_fit_rows": ent_console.archetype_fit_dashboard_rows(),
    }


@router.get(
    "/personas/overlap-report",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    summary="Persona scope overlap report (`sak482-f`)",
    responses=admin_bff_json_openapi_responses(),  # sak520-b
)
def admin_persona_overlap_report(_admin: AdminDep, orch: OrchDep) -> dict[str, Any]:
    shelf = load_shelf(orch)
    rows = persona_scope_overlap_report(shelf)
    table_rows = [
        {
            "business_area": str(r.get("business_area_id", "")),
            "development_role": str(r.get("development_role_id", "")),
            "overlap": ", ".join(str(t) for t in (r.get("overlap_tags") or [])),
            "count": str(r.get("overlap_count", 0)),
        }
        for r in rows
    ]
    warning = ""
    if rows:
        warning = (
            f"{len(rows)} shelf pair(s) have overlapping scope_in — assign personas carefully."
        )
    return {"pair_count": len(rows), "warning": warning, "rows": table_rows}


class FleetAutopilotPolicyBody(BaseModel):
    max_autopilot_level: int = Field(ge=0, le=10, default=10)
    required_checkpoints: list[str] = Field(default_factory=list)


class FleetEnforcementPolicyBody(BaseModel):
    min_enforcement_level: int = Field(ge=0, le=10, default=0)
    max_enforcement_level: int = Field(ge=0, le=10, default=10)


@router.get(
    "/enterprise/fleet-autopilot-policy",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    summary="Fleet autopilot policy GET (`sak482-f`)",
    responses=admin_bff_json_openapi_responses(),  # sak520-c
)
def enterprise_fleet_autopilot_policy_get(
    _admin: AdminDep,
    iam: IamStoreDep,
    api_key: Annotated[str, Depends(_require_enterprise_api_key)],
    tenant_id: str = Query(default=""),
) -> dict[str, Any]:
    slug = ""
    if tenant_id.strip():
        tid = _resolve_tenant_uuid(iam, tenant_id)
        for tenant in iam.list_tenants():
            if str(tenant.tenant_id) == tid:
                slug = tenant.slug
                break
        if not slug:
            slug = tenant_id.strip()
    policy = tenant_autopilot_policy(slug or None)
    return {
        **policy.to_dict(),
        "checkpoint_catalog": sorted(CHECKPOINT_CATALOG),
    }


@router.put(
    "/enterprise/fleet-autopilot-policy",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    summary="Fleet autopilot policy PUT (`sak482-f`)",
    responses=admin_bff_json_openapi_responses(),  # sak520-c
)
def enterprise_fleet_autopilot_policy_put(
    body: FleetAutopilotPolicyBody,
    _admin: AdminDep,
    iam: IamStoreDep,
    api_key: Annotated[str, Depends(_require_enterprise_api_key)],
    tenant_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    slug = ""
    tid = _resolve_tenant_uuid(iam, tenant_id)
    for tenant in iam.list_tenants():
        if str(tenant.tenant_id) == tid:
            slug = tenant.slug
            break
    if not slug:
        slug = tenant_id.strip()
    checkpoints = {c for c in body.required_checkpoints if c in CHECKPOINT_CATALOG}
    policy = FleetAutopilotPolicy(
        tenant_slug=slug,
        max_autopilot_level=body.max_autopilot_level,
        required_checkpoints=frozenset(checkpoints),
    )
    policies = load_fleet_autopilot_policies()
    policies[slug] = policy
    save_fleet_autopilot_policies(policies)
    return policy.to_dict()


@router.get(
    "/enterprise/fleet-enforcement-policy",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    summary="Fleet enforcement policy GET (`sak482-f`)",
    responses=admin_bff_json_openapi_responses(),  # sak520-g
)
def enterprise_fleet_enforcement_policy_get(
    _admin: AdminDep,
    iam: IamStoreDep,
    api_key: Annotated[str, Depends(_require_enterprise_api_key)],
    tenant_id: str = Query(default=""),
) -> dict[str, Any]:
    slug = ""
    if tenant_id.strip():
        tid = _resolve_tenant_uuid(iam, tenant_id)
        for tenant in iam.list_tenants():
            if str(tenant.tenant_id) == tid:
                slug = tenant.slug
                break
        if not slug:
            slug = tenant_id.strip()
    policy = tenant_enforcement_policy(slug or None)
    return policy.to_dict()


@router.put(
    "/enterprise/fleet-enforcement-policy",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    summary="Fleet enforcement policy PUT (`sak482-f`)",
    responses=admin_bff_json_openapi_responses(),  # sak520-h
)
def enterprise_fleet_enforcement_policy_put(
    body: FleetEnforcementPolicyBody,
    _admin: AdminDep,
    iam: IamStoreDep,
    api_key: Annotated[str, Depends(_require_enterprise_api_key)],
    tenant_id: Annotated[str, Query(min_length=1)],
) -> dict[str, Any]:
    if body.min_enforcement_level > body.max_enforcement_level:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "min_enforcement_level must be <= max_enforcement_level",
            ),
        )
    slug = ""
    tid = _resolve_tenant_uuid(iam, tenant_id)
    for tenant in iam.list_tenants():
        if str(tenant.tenant_id) == tid:
            slug = tenant.slug
            break
    if not slug:
        slug = tenant_id.strip()
    policy = FleetEnforcementPolicy(
        tenant_slug=slug,
        min_enforcement_level=body.min_enforcement_level,
        max_enforcement_level=body.max_enforcement_level,
    )
    policies = load_fleet_enforcement_policies()
    policies[slug] = policy
    save_fleet_enforcement_policies(policies)
    return policy.to_dict()


@router.get(
    "/enterprise/fleet-compare",
    response_model=AdminProjectionResponse,
    response_model_exclude_none=True,
    summary="Fleet tenant compare (`sak482-f`; peel-aware `sak494-g`)",
    responses=admin_bff_json_openapi_responses(),
)
def enterprise_fleet_compare(
    _admin: AdminDep,
    store: StoreDep,
    iam: IamStoreDep,
    api_key: Annotated[str, Depends(_require_enterprise_api_key)],
    tenant_a: Annotated[str, Query(min_length=1)],
    tenant_b: Annotated[str, Query(min_length=1)],
    run_limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    tid_a = _resolve_tenant_uuid(iam, tenant_a)
    tid_b = _resolve_tenant_uuid(iam, tenant_b)
    if not tid_a or not tid_b:
        raise HTTPException(
            status_code=422,
            detail=problem("tenant_not_found", "tenant_a and tenant_b must resolve to UUIDs"),
        )
    try:
        uuid_a = UUID(tid_a)
        uuid_b = UUID(tid_b)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_tenant", str(exc)),
        ) from exc
    compare = compare_tenant_metrics(
        store,
        tenant_a=uuid_a,
        tenant_b=uuid_b,
        run_limit=run_limit,
    )
    rows = ent_console.fleet_compare_table_rows(compare)
    return {
        "compare": compare,
        "caption": ent_console.fleet_compare_caption(compare),
        "rows": rows,
        "csv": ent_console.fleet_compare_csv(rows),
        "tenant_a": tid_a,
        "tenant_b": tid_b,
    }


@router.get(
    "/runs/{run_id}/timeline-panels",
    response_model=TimelinePanelsResponse,
    responses=admin_bff_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f
    summary="Timeline panels projection (`sak482-f`)",
)
def admin_ui_timeline_panels(run_id: UUID, store: StoreDep, _admin: AdminDep) -> dict[str, Any]:
    """Projection summaries for React admin — same read path as ``GET /runs/{id}/timeline``."""
    events = timeline_events_from_store(store, run_id)
    return build_timeline_panels_payload(events, run_id=run_id)
