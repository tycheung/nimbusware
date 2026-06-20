from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from agent_core.models import serialize_event_persistent, validate_event_dict
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import IamStoreDep, OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.personas_helpers import load_shelf
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_console import enterprise_console as ent_console
from nimbusware_console.critic_matrix_display import critic_matrix_rows_from_events
from nimbusware_console.critic_reliability_display import (
    critic_reliability_caption,
    critic_reliability_summary_from_events,
    critic_reliability_table_rows,
    fleet_critic_reliability_caption,
    fleet_critic_reliability_table_rows,
)
from nimbusware_console.findings_display import findings_list_from_response, findings_table_rows
from nimbusware_console.integration_adapter_writer_workflow_explainer import (
    integration_adapter_writer_from_events,
    integration_adapter_writer_run_caption,
    integration_adapter_writer_run_table_rows,
)
from nimbusware_console.operator_chat_core import ChatState, process_user_message
from nimbusware_console.services import enterprise as enterprise_svc
from nimbusware_env.edition import is_enterprise
from nimbusware_extensions.persona_scope_overlap import persona_scope_overlap_report
from nimbusware_iam.constants import API_KEY_HEADER
from nimbusware_orchestrator.autopilot_profiles import CHECKPOINT_CATALOG
from nimbusware_orchestrator.fleet_analytics import compare_tenant_metrics
from nimbusware_orchestrator.fleet_autopilot_policy import (
    FleetAutopilotPolicy,
    load_fleet_autopilot_policies,
    save_fleet_autopilot_policies,
    tenant_autopilot_policy,
)
from nimbusware_orchestrator.fleet_enforcement_policy import (
    FleetEnforcementPolicy,
    load_fleet_enforcement_policies,
    save_fleet_enforcement_policies,
    tenant_enforcement_policy,
)
from nimbusware_store.protocol import serialized_event_from_row

router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])

_chat_sessions: dict[str, ChatState] = {}


class OperatorChatMessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class OperatorChatMessageResponse(BaseModel):
    reply: str
    last_run_id: str = ""
    classification: dict[str, Any] | None = None


@router.post("/operator-chat/message", response_model=OperatorChatMessageResponse)
def operator_chat_message(
    body: OperatorChatMessageBody,
    _admin: AdminDep,
    x_nimbusware_chat_session: str | None = Header(default=None),
) -> OperatorChatMessageResponse:
    key = (x_nimbusware_chat_session or "default").strip()[:128] or "default"
    state = _chat_sessions.setdefault(key, ChatState())
    reply = process_user_message(body.text, state)
    return OperatorChatMessageResponse(
        reply=reply,
        last_run_id=state.last_run_id,
        classification=state.last_classification,
    )


@router.get(
    "/runs/{run_id}/findings-table",
    responses={404: PROBLEM_RESPONSE_404},
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
    responses={404: PROBLEM_RESPONSE_404},
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
    responses={404: PROBLEM_RESPONSE_404},
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
    responses={404: PROBLEM_RESPONSE_404},
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
    x_nimbusware_api_key: str | None = Header(default=None, alias=API_KEY_HEADER),
) -> str:
    if not is_enterprise():
        raise HTTPException(
            status_code=404,
            detail=problem(
                "enterprise_edition_required",
                "Fleet dashboard requires NIMBUSWARE_EDITION=enterprise",
            ),
        )
    key = (x_nimbusware_api_key or "").strip()
    if not key:
        raise HTTPException(
            status_code=401,
            detail=problem(
                "api_key_required",
                f"Enterprise fleet dashboard requires {API_KEY_HEADER}",
            ),
        )
    return key


@router.get("/enterprise/fleet-dashboard")
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
    return {
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
    }


@router.get("/personas/overlap-report")
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


@router.get("/enterprise/fleet-autopilot-policy")
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


@router.put("/enterprise/fleet-autopilot-policy")
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


@router.get("/enterprise/fleet-enforcement-policy")
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


@router.put("/enterprise/fleet-enforcement-policy")
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


@router.get("/enterprise/fleet-compare")
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
