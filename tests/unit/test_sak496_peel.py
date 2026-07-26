from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from orchestrator._pipeline.agent_evaluator_policy_llm_emit import (
    resolve_agent_evaluator_policy_llm_for_host,
)
from orchestrator._pipeline.self_refinement_critique_emit import (
    try_emit_self_refinement_critique_for_host,
)
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.workflow.agent_evaluator import (
    AgentEvaluatorAutoCreatePersonaBlock,
    AgentEvaluatorWorkflowBlock,
)

_ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def _patched_plan_stage(
    orch: Any,
    *,
    model_id: str | None = "dev:primary",
    llm_raises: BaseException | None = None,
) -> Iterator[tuple[MagicMock, MagicMock]]:
    llm_kwargs: dict[str, Any] = {"side_effect": llm_raises} if llm_raises is not None else {}
    with (
        patch.object(orch, "_maybe_emit_research_stages"),
        patch.object(orch, "_maybe_emit_stitch_stages"),
        patch.object(orch, "_run_created_metadata", return_value={}),
        patch(
            "research.reresearch.maybe_reresearch_after_plan_fail",
            return_value=False,
        ),
        patch.object(orch, "_selected_model_for_run", return_value=model_id),
        patch(
            "orchestrator._pipeline.lifecycle_plan.execute_plan_stage_llm",
            **llm_kwargs,
        ) as mock_llm,
        patch(
            "orchestrator._pipeline.lifecycle_plan.emit_stub_plan_stage",
        ) as mock_stub,
    ):
        yield mock_llm, mock_stub


# --- sak496-a: lifecycle_plan refuses stub fallback under LLM=1|2 ---


def test_sak496_a_source_markers() -> None:
    """sak496-a: lifecycle_plan propagates broker_miss instead of stub fallback."""
    lifecycle_plan = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "lifecycle_plan.py"
    ).read_text(encoding="utf-8")
    assert "sak496-a" in lifecycle_plan
    assert "broker_llm_enabled()" in lifecycle_plan
    assert "broker_miss: lifecycle_plan" in lifecycle_plan


def test_sak496_a_peel_broker_miss_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak496-a: LLM=1 — broker_miss from plan LLM propagates (no stub fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=RuntimeError("broker_miss: plan_stage: down"),
    ) as (_mock_llm, mock_stub):
        with pytest.raises(RuntimeError, match="broker_miss"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


def test_sak496_a_peel_runtime_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak496-a: LLM=1 — non-broker RuntimeError propagates (no stub fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=RuntimeError("invalid plan panel"),
    ) as (_mock_llm, mock_stub):
        with pytest.raises(RuntimeError, match="invalid plan panel"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


def test_sak496_a_peel_value_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak496-a: LLM=2 — non-transport ValueError propagates under peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=ValueError("bad payload"),
    ) as (_mock_llm, mock_stub):
        with pytest.raises(ValueError, match="bad payload"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


def test_sak496_a_peel_no_model_raises_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak496-a: LLM=1 — missing model raises broker_miss (no stub fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(orch, model_id=None) as (mock_llm, mock_stub):
        with pytest.raises(RuntimeError, match="broker_miss: lifecycle_plan"):
            orch.execute_plan_stage(run_id)
    mock_llm.assert_not_called()
    mock_stub.assert_not_called()


def test_sak496_a_peel_off_runtime_error_stub_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-a / sak499-e: LLM=0 — broker_miss/transport soft-falls; other RuntimeError raises."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(
        orch,
        llm_raises=RuntimeError("broker_miss: plan_stage: down"),
    ) as (_mock_llm, mock_stub):
        orch.execute_plan_stage(run_id)
    mock_stub.assert_called_once()

    with _patched_plan_stage(
        orch,
        llm_raises=RuntimeError("invalid plan panel"),
    ) as (_mock_llm, mock_stub):
        with pytest.raises(RuntimeError, match="invalid plan panel"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


# --- sak496-b: removed-LLM emit paths (agent_eval / self_refinement / backlog) ---


def test_sak496_b_source_markers() -> None:
    """sak496-b: emit modules refuse stub/rules/heuristic fallback under LLM peel."""
    agent_eval = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "agent_evaluator_policy_llm_emit.py"
    ).read_text(encoding="utf-8")
    sr = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "self_refinement_critique_emit.py"
    ).read_text(encoding="utf-8")
    generator = (_ROOT / "packages" / "orchestrator" / "campaign" / "generator.py").read_text(
        encoding="utf-8"
    )
    assert "sak496-b" in agent_eval
    assert "broker_llm_enabled()" in agent_eval
    assert "sak496-b" in sr
    assert "broker_llm_enabled()" in sr
    assert "sak497-c" in generator
    assert "broker_llm_enabled()" in generator


def test_sak496_b_agent_evaluator_peel_on_llm_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-b: agent evaluator policy LLM None under peel — no stub/rules fallback."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    block = AgentEvaluatorWorkflowBlock(
        enabled=True,
        persona_id="commerce",
        llm_evaluation_enabled=True,
        auto_create_persona=AgentEvaluatorAutoCreatePersonaBlock(),
    )
    host = MagicMock()
    host._selected_model_for_run.return_value = "stub-model"
    host._base_cfg.return_value = {"runtime": {"base_url": "http://127.0.0.1:1"}}
    rules_eval: dict[str, Any] = {"status": "ok", "gaps": [], "score": 0.5}
    with patch(
        "orchestrator._pipeline.agent_evaluator_policy_llm_emit.execute_agent_evaluator_policy_llm",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match="broker_miss: agent_evaluator_policy_llm_emit"):
            resolve_agent_evaluator_policy_llm_for_host(
                host,
                uuid4(),
                block=block,
                rules_eval=rules_eval,
            )


def test_sak496_b_agent_evaluator_peel_off_llm_none_stub_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-b: peel off — agent evaluator stub env still applies when LLM returns None."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_AGENT_EVALUATOR_LLM_STUB", "1")
    block = AgentEvaluatorWorkflowBlock(
        enabled=True,
        persona_id="commerce",
        llm_evaluation_enabled=True,
        auto_create_persona=AgentEvaluatorAutoCreatePersonaBlock(),
    )
    host = MagicMock()
    host._selected_model_for_run.return_value = "stub-model"
    host._base_cfg.return_value = {"runtime": {"base_url": "http://127.0.0.1:1"}}
    rules_eval: dict[str, Any] = {"status": "ok", "gaps": []}
    with patch(
        "orchestrator._pipeline.agent_evaluator_policy_llm_emit.execute_agent_evaluator_policy_llm",
        return_value=None,
    ):
        branch, mode, meta = resolve_agent_evaluator_policy_llm_for_host(
            host,
            uuid4(),
            block=block,
            rules_eval=rules_eval,
        )
    assert branch == "rules_with_llm_policy"
    assert mode == "stub"
    assert isinstance(meta, dict)


def test_sak496_b_self_refinement_peel_on_llm_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-b: self-refinement critique LLM None under peel — no stub panel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_SELF_REFINEMENT_CRITIQUE_STUB", "1")
    host = MagicMock()
    host._repo_root = _ROOT
    host._config_materializer = None
    host._selected_model_for_run.return_value = "stub-model"
    host._base_cfg.return_value = {"runtime": {"base_url": "http://127.0.0.1:1"}}
    with (
        patch(
            "orchestrator._pipeline.self_refinement_critique_emit.self_refinement_llm_critique_effective_for_run",
            return_value=True,
        ),
        patch(
            "orchestrator._pipeline.self_refinement_critique_emit.execute_self_refinement_critique_llm",
            return_value=None,
        ),
        patch(
            "orchestrator._pipeline.self_refinement_critique_emit.emit_stub_self_refinement_critique_panel",
        ) as mock_stub,
    ):
        with pytest.raises(RuntimeError, match="self_refinement critique LLM local path removed"):
            try_emit_self_refinement_critique_for_host(
                host,
                uuid4(),
                llm_critique_enabled=True,
                gate_decision="hold",
                workflow_profile="nimbusware_production",
                workflow_block=object(),
                evaluation_status="gap",
                gaps=["missing depth"],
                description="test",
            )
    assert mock_stub.call_count == 0


# --- sak496-g: LLM chat SSE peel + export 503 OpenAPI ---


def test_sak496_g_source_markers() -> None:
    """sak496-g: chat stream uses LLM peel; run SSE streams stay COMPUTE peel."""
    sse = (_ROOT / "packages" / "api" / "sse_peel.py").read_text(encoding="utf-8")
    chat_stream = (_ROOT / "packages" / "api" / "routes" / "chat_stream.py").read_text(
        encoding="utf-8",
    )
    maker_stream = (_ROOT / "packages" / "api" / "routes" / "runs" / "stream.py").read_text(
        encoding="utf-8",
    )
    theater = (_ROOT / "packages" / "api" / "routes" / "runs" / "theater.py").read_text(
        encoding="utf-8",
    )
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak496-g" in sse
    assert "early_llm_sse_peel_miss" in sse
    assert "broker_llm_enabled()" in sse
    assert "early_llm_sse_peel_miss" in chat_stream
    assert "llm_json_openapi_responses" in chat_stream
    assert "early_sse_peel_miss" in maker_stream
    assert "early_sse_peel_miss" in theater
    assert "export_openapi_responses" in theater
    assert "export_openapi_responses" in peel


def test_sak496_g_llm_chat_sse_peel_on_returns_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-g: LLM=1 — chat SSE peel returns broker_miss error frame."""
    from api.sse_peel import early_llm_sse_peel_miss

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    frame = early_llm_sse_peel_miss(feature="chat_session_stream")
    assert frame is not None
    assert "broker_miss" in frame
    assert "chat_session_stream" in frame
    assert "degraded" in frame


def test_sak496_g_llm_chat_sse_peel_off_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-g: LLM=0 — chat SSE peel guard does not block local stream."""
    from api.sse_peel import early_llm_sse_peel_miss

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    assert early_llm_sse_peel_miss(feature="chat_session_stream") is None


def test_sak496_g_llm_chat_sse_peel_only_raises_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-g: LLM=2 — chat SSE peel raises broker_llm_unavailable 503."""
    from fastapi import HTTPException

    from api.sse_peel import early_llm_sse_peel_miss

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    with pytest.raises(HTTPException) as ei:
        early_llm_sse_peel_miss(feature="chat_session_stream")
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_llm_unavailable"


def test_sak496_g_export_openapi_includes_503() -> None:
    """sak496-g: export OpenAPI helper documents broker-only 503."""
    from api.schemas.peel_responses import export_openapi_responses

    responses = export_openapi_responses()
    assert 503 in responses


# --- sak496-e: enterprise peel OpenAPI 503 sweep ---

import json

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses

SAK496_E_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/fleet-learnings/search", "get"),
    ("/v1/enterprise/fleet/critic-reliability", "get"),
    ("/v1/users", "get"),
    ("/v1/enterprise/iam/bootstrap", "post"),
    ("/v1/enterprise/iam/me", "get"),
    ("/v1/enterprise/tenants", "get"),
    ("/v1/enterprise/tenants", "post"),
    ("/v1/enterprise/tenants/{tenant_id}/api-keys", "post"),
    ("/v1/enterprise/scraper-artifacts/storage", "get"),
    ("/v1/enterprise/config-notify/status", "get"),
    ("/v1/enterprise/compliance/summary", "get"),
    ("/v1/enterprise/audit-export", "get"),
)


def _sak496_e_openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


@pytest.mark.sak496_e
def test_sak496_e_openapi_artifact_documents_peel_503() -> None:
    """sak496-e: openapi.json lists 503 problem+json on enterprise peel paths."""
    spec = json.loads(_sak496_e_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK496_E_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


@pytest.mark.sak496_e
def test_sak496_e_peel_routes_source_wire_openapi_helpers() -> None:
    """sak496-e: enterprise peel routes wire enterprise_peel_json_openapi_responses."""
    root = _ROOT / "packages" / "api"
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    fleet_learnings = (root / "routes" / "enterprise" / "fleet_learnings.py").read_text(
        encoding="utf-8"
    )
    critic = (root / "routes" / "enterprise" / "fleet_critic_reliability.py").read_text(
        encoding="utf-8"
    )
    users = (root / "routes" / "enterprise" / "users.py").read_text(encoding="utf-8")
    iam = (root / "routes" / "enterprise" / "iam.py").read_text(encoding="utf-8")
    object_store = (root / "routes" / "enterprise" / "object_store.py").read_text(encoding="utf-8")
    config_notify = (root / "routes" / "enterprise" / "config_notify.py").read_text(
        encoding="utf-8"
    )
    compliance = (root / "routes" / "enterprise" / "compliance.py").read_text(encoding="utf-8")
    audit_export = (root / "routes" / "enterprise" / "audit_export.py").read_text(encoding="utf-8")

    assert "sak496-e" in peel
    assert enterprise_peel_json_openapi_responses()[503] is PROBLEM_RESPONSE_503

    assert "/search" in fleet_learnings
    assert "responses=enterprise_peel_json_openapi_responses" in fleet_learnings
    assert "sak496-e" in fleet_learnings

    assert "responses=enterprise_peel_json_openapi_responses" in critic
    assert "sak496-e" in critic

    assert "/users" in users
    assert "responses=enterprise_peel_json_openapi_responses" in users

    assert iam.count("responses=enterprise_peel_json_openapi_responses") >= 5
    assert "sak496-e" in iam

    assert "/storage" in object_store
    assert "responses=enterprise_peel_json_openapi_responses" in object_store

    assert "/status" in config_notify
    assert "responses=enterprise_peel_json_openapi_responses" in config_notify

    assert "/compliance/summary" in compliance
    assert "responses=enterprise_peel_json_openapi_responses" in compliance

    assert "/audit-export" in audit_export
    assert "enterprise_peel_json_openapi_responses" in audit_export
    assert "sak496-e" in audit_export


# --- sak496-f: runs/maker + BFF OpenAPI 503 (404 only where peel applies) ---

from api.schemas.peel_responses import (
    admin_bff_json_openapi_responses,
    long_tail_json_openapi_responses,
    memory_json_openapi_responses,
    platform_peel_json_openapi_responses,
    research_json_openapi_responses,
    runs_json_openapi_responses,
)

SAK496_F_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/research", "get"),
    ("/v1/runs/{run_id}/research/{brief_id}/approve", "post"),
    ("/v1/runs/{run_id}/research/{brief_id}/reject", "post"),
    ("/v1/runs/{run_id}/memory-chunks/{chunk_id}/insert", "post"),
    ("/v1/runs/{run_id}/learnings", "get"),
    ("/v1/runs/{run_id}/maker-progress", "get"),
    ("/v1/admin/ui/runs/{run_id}/findings-table", "get"),
    ("/v1/admin/ui/runs/{run_id}/critic-matrix-table", "get"),
    ("/v1/admin/ui/runs/{run_id}/integration-adapter-writer", "get"),
    ("/v1/admin/ui/runs/{run_id}/critic-reliability", "get"),
    ("/v1/admin/ui/runs/{run_id}/timeline-panels", "get"),
    ("/v1/platform/collab-disciplines", "get"),
    ("/v1/platform/workspace-scaffold", "post"),
    ("/v1/platform/provider-subscriptions/{provider_id}/oauth/authorize", "get"),
    ("/v1/platform/provider-subscriptions/oauth/callback", "get"),
)


@pytest.mark.sak496_f
def test_sak496_f_openapi_artifact_documents_peel_503() -> None:
    """sak496-f: openapi.json lists 503 problem+json on runs/maker/BFF peel paths."""
    spec = json.loads(_sak496_e_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK496_F_PEEL_OPENAPI:
        content = (
            spec.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get("503", {})
            .get("content", {})
            or {}
        )
        assert "application/problem+json" in content, (
            f"missing 503 problem+json on {method.upper()} {path}"
        )
        schema = content["application/problem+json"].get("schema", {})
        assert schema.get("type") == "object"
        assert "code" in schema.get("properties", {})


@pytest.mark.sak496_f
def test_sak496_f_peel_routes_source_wire_openapi_helpers() -> None:
    """sak496-f: runs/maker/BFF routes wire peel OpenAPI helpers (404 only where applicable)."""
    root = _ROOT / "packages" / "api"
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    research = (root / "routes" / "runs" / "research.py").read_text(encoding="utf-8")
    memory_insert = (root / "routes" / "runs" / "memory_insert.py").read_text(encoding="utf-8")
    learnings = (root / "routes" / "runs" / "learnings.py").read_text(encoding="utf-8")
    maker_progress = (root / "routes" / "runs" / "maker_progress.py").read_text(encoding="utf-8")
    bff = (root / "routes" / "admin_ui_bff.py").read_text(encoding="utf-8")
    platform = (root / "routes" / "platform.py").read_text(encoding="utf-8")
    oauth = (root / "routes" / "provider_subscription_oauth.py").read_text(encoding="utf-8")

    assert "sak496-f" in peel
    assert runs_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert research_json_openapi_responses(not_found={"x": 1})[404] == {"x": 1}
    assert memory_json_openapi_responses(not_found={"x": 1})[404] == {"x": 1}
    assert admin_bff_json_openapi_responses(not_found={"x": 1})[404] == {"x": 1}
    assert platform_peel_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert long_tail_json_openapi_responses()[503] is PROBLEM_RESPONSE_503

    assert research.count("research_json_openapi_responses") >= 3
    assert "sak496-f" in research
    assert "memory_json_openapi_responses" in memory_insert
    assert "sak496-f" in memory_insert
    assert "runs_json_openapi_responses" in learnings
    assert "sak496-f" in learnings
    assert "runs_json_openapi_responses" in maker_progress
    assert "sak496-f" in maker_progress

    assert bff.count("admin_bff_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)") >= 5
    assert "sak496-f" in bff

    assert "/collab-disciplines" in platform
    assert "platform_peel_json_openapi_responses" in platform
    assert "/workspace-scaffold" in platform
    assert "sak496-f" in platform

    assert "/oauth/authorize" in oauth
    assert "/oauth/callback" in oauth
    assert "long_tail_json_openapi_responses" in oauth
    assert "sak496-f" in oauth


# --- sak496-d: research / egress / sandbox / tools broker_route facades ---


def test_sak496_d_source_markers() -> None:
    """sak496-d: domain broker_route modules + wired call sites."""
    research_route = (_ROOT / "packages" / "research" / "broker_route.py").read_text(
        encoding="utf-8",
    )
    egress_route = (_ROOT / "packages" / "executor" / "broker_route.py").read_text(
        encoding="utf-8",
    )
    tools_route = (_ROOT / "packages" / "agent_tools" / "broker_route.py").read_text(
        encoding="utf-8",
    )
    research_fetch = (_ROOT / "packages" / "research" / "fetch.py").read_text(encoding="utf-8")
    executor_fetch = (_ROOT / "packages" / "executor" / "fetch.py").read_text(encoding="utf-8")
    shell_tools = (_ROOT / "packages" / "agent_tools" / "shell_tools.py").read_text(
        encoding="utf-8",
    )
    dual_run = (_ROOT / "packages" / "broker_client" / "dual_run_route.py").read_text(
        encoding="utf-8",
    )

    assert "sak496-d" in research_route
    assert "map_domain_broker_http_miss" in research_route  # sak499-f
    assert "sak496-d" in egress_route
    assert "map_domain_broker_http_miss" in egress_route  # sak499-f
    assert "sak496-d" in tools_route
    assert "map_domain_broker_http_miss" in tools_route  # sak499-f
    assert "raise_research_peel_miss" in research_fetch
    assert "raise_egress_peel_miss" in executor_fetch
    assert "agent_tools.broker_route" in shell_tools
    assert "research.broker_route" in dual_run
    assert "executor.broker_route" in dual_run
    assert "agent_tools.broker_route" in dual_run


def test_sak496_d_domain_peel_miss_mappers() -> None:
    """sak496-d: build_domain_peel_miss shared by research/egress/sandbox/tools routes."""
    from agent_tools import broker_route as tools_route
    from broker_client.dual_run_route import build_domain_peel_miss
    from executor import broker_route as egress_route
    from research import broker_route as research_route

    body = build_domain_peel_miss("down", feature="research_fetch")
    assert body["via"] == "broker_miss"
    assert body["status"] == "degraded"
    assert body["feature"] == "research_fetch"
    assert callable(research_route.map_broker_research_http_miss)
    assert callable(egress_route.map_broker_egress_http_miss)
    assert callable(tools_route.map_broker_sandbox_http_miss)
    assert callable(tools_route.map_broker_tools_http_miss)


def test_sak496_d_research_fetch_peel_on_broker_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-d: RESEARCH=1 — broker None raises via broker_route peel miss."""
    from research.fetch import fetch_url

    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    monkeypatch.setattr(
        "research.research_bridge.try_broker_research_fetch",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="broker_miss: research_fetch"):
        fetch_url("https://example.com/page")


def test_sak496_d_egress_checked_peel_on_broker_none_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-d: EGRESS=1 — broker None raises via broker_route peel miss."""
    from uuid import UUID

    import httpx

    from executor.fetch import egress_checked_httpx_get

    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    role = UUID("11111111-1111-4111-8111-111111111101")
    client = MagicMock(spec=httpx.Client)
    monkeypatch.setattr(
        "executor.egress_bridge.try_broker_egress_check",
        lambda _url: None,
    )
    with pytest.raises(RuntimeError, match="broker_miss: egress"):
        egress_checked_httpx_get(
            "https://example.com/path",
            actor_role_id=role,
            scraper_role_allowlist=[role],
            domain_allowlist=["example.com"],
            client=client,
        )
    client.get.assert_not_called()


def test_sak496_d_tool_run_shell_peel_raises_on_broker_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak496-d: SANDBOX=1 — broker None raises via agent_tools.broker_route."""
    from agent_tools.shell_tools import tool_run_shell

    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")
    local_called: list[object] = []

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: local_called.append(True),
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        with pytest.raises(RuntimeError, match="broker_miss: shell"):
            tool_run_shell(tmp_path, "pytest", ["-q"])

    assert local_called == []


# --- sak496-c: critique / test_writer LLM peel_strict residuals ---


def test_sak496_c_source_markers() -> None:
    """sak496-c: critique + test_writer propagate non-transport peel errors."""
    critique = (_ROOT / "packages" / "orchestrator" / "critique" / "llm.py").read_text(
        encoding="utf-8",
    )
    tw = (_ROOT / "packages" / "orchestrator" / "test_writer_stage.py").read_text(
        encoding="utf-8",
    )
    assert "sak496-c" in critique
    assert "broker_llm_enabled()" in critique
    assert "peel_strict=True" in critique
    assert "sak496-c" in tw
    assert "peel_strict=True" in tw


# --- sak496-h: admin isComputeMiss no longer treats bare error as miss ---


def test_sak496_h_admin_compute_miss_markers() -> None:
    """sak496-h: peel_assert.ts isComputeMiss requires structured peel signals."""
    peel = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8"
    )
    peel_test = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.test.ts").read_text(
        encoding="utf-8"
    )
    assert "sak496-h" in peel or "isComputeMiss" in peel
    assert 'body.via === "broker_miss"' in peel or 'via === "broker_miss"' in peel
    assert "bare error" in peel_test or "validation failed" in peel_test
    assert "isComputeMiss({ error:" in peel_test


# --- sak496-i: domain peel_assert + SDK miss detectors ---


def test_sak496_i_domain_peel_assert_markers() -> None:
    """sak496-i: peel_assert.py domain miss detectors wired."""
    peel = (_ROOT / "packages" / "broker_client" / "peel_assert.py").read_text(
        encoding="utf-8",
    )
    assert "sak496-i" in peel
    assert "is_sandbox_miss" in peel
    assert "is_llm_miss" in peel
    assert "assert_sandbox_ok" in peel
    assert "assert_llm_ok" in peel


def test_sak496_i_domain_peel_assert_detectors() -> None:
    """sak496-i: domain miss detectors classify structured broker bodies."""
    from broker_client.peel_assert import (
        assert_llm_ok,
        assert_sandbox_ok,
        is_llm_miss,
        is_sandbox_miss,
    )

    assert is_sandbox_miss({"code": "broker_sandbox_only"}) is True
    assert is_sandbox_miss({"stdout": "ok", "via": "broker"}) is False
    assert is_llm_miss({"code": "broker_llm_unavailable"}) is True
    assert is_llm_miss({"content": "hi", "via": "broker"}) is False
    assert_sandbox_ok({"stdout": "ok"}, feature="shell")
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_llm_ok({"via": "broker_miss", "error": "down"}, feature="llm_chat")


def test_sak496_i_sdk_domain_miss_markers() -> None:
    """sak496-i: SwissArmyNoife SDK domain miss detectors tagged."""
    py = (
        _ROOT.parent / "SwissArmyNoife" / "sdks" / "python" / "src" / "swissarmynoife" / "client.py"
    ).read_text(encoding="utf-8")
    ts = (_ROOT.parent / "SwissArmyNoife" / "sdks" / "typescript" / "src" / "index.ts").read_text(
        encoding="utf-8"
    )
    rust = (_ROOT.parent / "SwissArmyNoife" / "crates" / "sdk" / "src" / "client.rs").read_text(
        encoding="utf-8",
    )
    assert "sak496-i" in py
    assert "is_sandbox_miss" in py
    assert "is_llm_miss" in py
    assert "sak496-i" in ts
    assert "sak496-i" in rust


# --- sak496-j: Maker long-tail miss aggregation + write-path toasts ---


def _maker_js_root() -> Path:
    return _ROOT / "packages" / "maker_web" / "static" / "js"


def test_sak496_j_maker_long_tail_miss_markers() -> None:
    """sak496-j: chat drawer / review / ribbon aggregate partial multi-fetch misses."""
    tabs = _maker_js_root() / "tabs"
    drawer = (tabs / "chat_model_drawer_ui.js").read_text(encoding="utf-8")
    review = (tabs / "review.js").read_text(encoding="utf-8")
    ribbon = (tabs / "progress" / "progress_ribbon_refresh.js").read_text(encoding="utf-8")
    broker_miss = (_maker_js_root() / "broker_miss.js").read_text(encoding="utf-8")
    assert "sak496-j" in drawer
    assert "toastIfMisses" in drawer
    assert "sak496-j" in review
    assert "toastIfMiss" in review
    assert "Plan approve unavailable" in review
    assert "sak496-j" in ribbon
    assert "toastIfMisses" in ribbon
    assert "toastIfMisses" in broker_miss
    assert "sak496-j" in broker_miss
