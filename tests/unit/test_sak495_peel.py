from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from extensions.extension_runtime import UniversalCritiqueRouter
from memory.peel_index.contribution import maybe_rebuild_memory_index_for_run
from orchestrator._pipeline.create_run import CreateRunMixin
from orchestrator.context_artifacts import maybe_rebuild_memory_faiss_from_bridges
from orchestrator.refactor_stage import emit_refactor_stage_and_critique
from orchestrator.registry import RoleRegistry
from orchestrator.test_writer_stage import run_test_writer_stage
from orchestrator.workflow.refactor import RefactorWorkflowBlock
from store.memory import InMemoryEventStore

_ROOT = Path(__file__).resolve().parents[2]


# --- sak495-a: refuse local index contribution/rebuild under MEMORY=1|2 ---


def test_sak495_a_source_markers() -> None:
    """sak495-a: run-create, slice, FAISS bridge refuse local peel_index under MEMORY=1|2."""
    create_run = (_ROOT / "packages" / "orchestrator" / "_pipeline" / "create_run.py").read_text(
        encoding="utf-8",
    )
    contribution = (_ROOT / "packages" / "memory" / "peel_index" / "contribution.py").read_text(
        encoding="utf-8",
    )
    context = (_ROOT / "packages" / "orchestrator" / "context_artifacts.py").read_text(
        encoding="utf-8",
    )
    executor = (_ROOT / "packages" / "orchestrator" / "slice" / "executor.py").read_text(
        encoding="utf-8",
    )
    implement = (
        _ROOT / "packages" / "maker" / "slice_workflow" / "implement_panel.py"
    ).read_text(encoding="utf-8")
    route = (_ROOT / "packages" / "memory" / "broker_route.py").read_text(encoding="utf-8")

    assert "sak495-a" in contribution
    assert "refuse_legacy" in contribution
    assert "broker_memory_enabled" in contribution
    assert "sak495-a" in create_run
    assert "sak495-a" in context
    assert "broker_memory_enabled" in context
    assert "sak495-a" in executor
    assert "sak495-a" in implement
    assert "sak495-a" in route


@pytest.mark.sak495_a
def test_contribution_refuses_under_memory_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """sak495-a: MEMORY=1 refuses run index contribution via refuse_legacy."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    with pytest.raises(RuntimeError, match=r"MEMORY=1\|2"):
        maybe_rebuild_memory_index_for_run(
            object(),
            object(),
            run_id=uuid4(),
            repo_root=tmp_path,
            run_created_metadata={"memory": {"index_contribution": True}},
        )


@pytest.mark.sak495_a
def test_contribution_refuses_under_memory_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """sak495-a: MEMORY=2 refuses run index contribution via refuse_legacy."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    with pytest.raises(RuntimeError, match=r"MEMORY=1\|2"):
        maybe_rebuild_memory_index_for_run(
            object(),
            object(),
            run_id=uuid4(),
            repo_root=tmp_path,
        )


@pytest.mark.sak495_a
def test_contribution_does_not_touch_peel_index_under_memory_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-a: MEMORY=1 gate fires before any peel_index indexer import."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    with (
        patch("memory.peel_index.indexer.deterministic_chunk_id") as indexer,
        pytest.raises(RuntimeError, match=r"MEMORY=1\|2"),
    ):
        maybe_rebuild_memory_index_for_run(
            object(),
            object(),
            run_id=uuid4(),
            repo_root=tmp_path,
        )
    indexer.assert_not_called()


@pytest.mark.sak495_a
def test_create_run_maybe_rebuild_refuses_under_memory_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-a: CreateRunMixin.maybe_rebuild_memory_index refuses under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    host = SimpleNamespace(
        _memory_chunk_store=object(),
        _store=object(),
        _repo_root=tmp_path,
    )
    run_id = uuid4()
    host._run_created_metadata = lambda _rid: {"memory": {"index_contribution": True}}

    with pytest.raises(RuntimeError, match=r"MEMORY=1\|2"):
        CreateRunMixin.maybe_rebuild_memory_index(host, run_id)


@pytest.mark.sak495_a
def test_faiss_bridge_skips_under_memory_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-a / sak498-i: FAISS rebuild raises under MEMORY=1 when rebuild env set."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv("NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD", "1")
    bridge_dir = tmp_path / ".cache" / "nimbusware" / "memory-bridge" / "proj"
    bridge_dir.mkdir(parents=True)
    (bridge_dir / "a.json").write_text(
        '{"artifact_id":"a","title":"t","excerpt":"hello bridge"}',
        encoding="utf-8",
    )
    with patch("memory.peel_index.embeddings.embed_text") as embed:
        with pytest.raises(RuntimeError, match="MEMORY=1\\|2"):
            maybe_rebuild_memory_faiss_from_bridges("proj", repo_root=tmp_path)
    embed.assert_not_called()


@pytest.mark.sak495_a
def test_faiss_bridge_skips_under_memory_2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-a / sak498-i: FAISS rebuild raises under MEMORY=2 when rebuild env set."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    monkeypatch.setenv("NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD", "1")
    with patch("memory.peel_index.faiss_index.build_memory_faiss_index") as build:
        with pytest.raises(RuntimeError, match="MEMORY=1\\|2"):
            maybe_rebuild_memory_faiss_from_bridges("proj", repo_root=tmp_path)
    build.assert_not_called()


# --- sak495-h: test_writer / refactor non-transport peel residuals ---


def test_sak495_h_source_markers() -> None:
    """sak495-h: test_writer + refactor refuse stub/code_intel on non-transport peel errors."""
    tw = (_ROOT / "packages" / "orchestrator" / "test_writer_stage.py").read_text(
        encoding="utf-8"
    )
    refactor = (_ROOT / "packages" / "orchestrator" / "refactor_stage.py").read_text(
        encoding="utf-8"
    )
    assert "sak495-h" in tw
    assert "sak495-h" in refactor
    assert "broker_llm_enabled()" in tw
    assert "broker_llm_enabled()" in refactor


def test_sak495_h_test_writer_peel_on_runtime_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak495-h: LLM=1 — non-broker RuntimeError propagates (no stub fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")

    with patch(
        "orchestrator.test_writer_stage.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("invalid llm panel"),
    ):
        with pytest.raises(RuntimeError, match="invalid llm panel"):
            run_test_writer_stage(
                Path("."),
                llm_body_enabled=True,
                llm_stub_fallback=True,
                llm_model_id="m",
            )


def test_sak495_h_test_writer_peel_on_value_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak495-h: LLM=2 — non-transport ValueError propagates under peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")

    with patch(
        "orchestrator.test_writer_stage.ollama_chat_json_via_plan_patch",
        side_effect=ValueError("bad payload"),
    ):
        with pytest.raises(ValueError, match="bad payload"):
            run_test_writer_stage(
                Path("."),
                llm_body_enabled=True,
                llm_stub_fallback=True,
                llm_model_id="m",
            )


def test_sak495_h_test_writer_peel_off_runtime_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak495-h / sak498-i: LLM=0 — non-broker RuntimeError propagates (no stub fallback)."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")

    with patch(
        "orchestrator.test_writer_stage.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("invalid llm panel"),
    ):
        with pytest.raises(RuntimeError, match="invalid llm panel"):
            run_test_writer_stage(
                Path("."),
                llm_body_enabled=True,
                llm_stub_fallback=True,
                llm_model_id="m",
            )


def test_sak495_h_refactor_peel_on_runtime_error_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-h: LLM=1 — non-broker RuntimeError propagates (no code_intel fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "orphan.py").write_text("X = 1\n", encoding="utf-8")

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    run_id = uuid4()

    with patch(
        "orchestrator.llm.chat_facade.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("invalid refactor payload"),
    ):
        with pytest.raises(RuntimeError, match="invalid refactor payload"):
            emit_refactor_stage_and_critique(
                store,
                registry,
                router,
                run_id=run_id,
                block=RefactorWorkflowBlock(
                    enabled=True,
                    stub_only=False,
                    llm_enabled=True,
                ),
                workspace=ws,
            )
    assert not store.list_run_events(str(run_id))


def test_sak495_h_refactor_peel_on_value_error_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-h: LLM=2 — non-transport ValueError propagates under peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "orphan.py").write_text("X = 1\n", encoding="utf-8")

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    run_id = uuid4()

    with patch(
        "orchestrator.llm.chat_facade.ollama_chat_json_via_plan_patch",
        side_effect=ValueError("shape mismatch"),
    ):
        with pytest.raises(ValueError, match="shape mismatch"):
            emit_refactor_stage_and_critique(
                store,
                registry,
                router,
                run_id=run_id,
                block=RefactorWorkflowBlock(
                    enabled=True,
                    stub_only=False,
                    llm_enabled=True,
                ),
                workspace=ws,
            )
    assert not store.list_run_events(str(run_id))


def test_sak495_h_refactor_peel_off_runtime_error_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-h: LLM=0 — non-broker RuntimeError still soft-falls back to code_intel."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "orphan.py").write_text("X = 1\n", encoding="utf-8")

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    run_id = uuid4()

    with patch(
        "orchestrator.llm.chat_facade.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("invalid refactor payload"),
    ), patch("orchestrator.refactor_stage.append_gate_decision_event"):
        emit_refactor_stage_and_critique(
            store,
            registry,
            router,
            run_id=run_id,
            block=RefactorWorkflowBlock(
                enabled=True,
                stub_only=False,
                llm_enabled=True,
            ),
            workspace=ws,
        )
    started = next(
        r
        for r in store.list_run_events(str(run_id))
        if r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "refactor"
    )
    meta = (started.get("metadata") or {}).get("refactor") or {}
    assert meta.get("mode") == "code_intel_proposal"


# --- sak495-b: slice/plan excerpt miss + micro_slice audit gating ---

from orchestrator.slice.micro_slice import parse_slice_plan
from orchestrator.workflow.memory import (
    MemoryWorkflowBlock,
    retrieve_memory_excerpt_for_slice,
)


def _stub_slice_plan():
    return parse_slice_plan(
        {
            "slice_id": "sak495-b",
            "rationale": "broker memory excerpt miss",
            "target_paths": ["packages/orchestrator/workflow/memory.py"],
            "acceptance_criteria": "raises on broker miss under MEMORY=1|2",
        },
    )


def test_sak495_b_wiring() -> None:
    """sak495-b: slice excerpt raises on miss; micro_slice audit gated under peel."""
    memory = (_ROOT / "packages" / "orchestrator" / "workflow" / "memory.py").read_text(
        encoding="utf-8",
    )
    micro = (_ROOT / "packages" / "orchestrator" / "_pipeline" / "micro_slice.py").read_text(
        encoding="utf-8",
    )
    assert "sak495-b" in memory
    assert "broker_miss: slice_memory" in memory
    assert "not broker_memory_enabled()" in micro
    assert "sak495-b" in micro


@pytest.mark.sak495_b
def test_sak495_b_slice_memory_raises_on_broker_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-b: MEMORY=1 broker None raises (no silent empty excerpt)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    settings = MemoryWorkflowBlock()
    with (
        patch("agent_tools.memory_bridge.try_broker_memory_search", return_value=None),
        patch("memory.peel_index.search.search_memory") as local_search,
        patch("memory.peel_index.search.search_user_memory") as user_search,
    ):
        with pytest.raises(RuntimeError, match="broker_miss: slice_memory"):
            retrieve_memory_excerpt_for_slice(
                object(),
                _stub_slice_plan(),
                repo_root=tmp_path,
                settings=settings,
            )
    local_search.assert_not_called()
    user_search.assert_not_called()


@pytest.mark.sak495_b
def test_sak495_b_slice_memory_broker_only_propagates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak495-b: MEMORY=2 broker failure propagates (no local fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    settings = MemoryWorkflowBlock()
    with (
        patch(
            "agent_tools.memory_bridge.try_broker_memory_search",
            side_effect=RuntimeError("broker_miss: slice_memory: down"),
        ),
        patch("memory.peel_index.search.search_memory") as local_search,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            retrieve_memory_excerpt_for_slice(
                object(),
                _stub_slice_plan(),
                repo_root=tmp_path,
                settings=settings,
            )
    local_search.assert_not_called()


# --- sak495-i: TOOLS dual-run peel miss ---

from unittest.mock import MagicMock

from agent_tools.shell_tools import tool_run_shell


@pytest.mark.sak495_i
def test_sak495_i_tool_run_shell_tools_peel_raises_on_broker_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak495-i: TOOLS=1 — broker None raises; no local tools fallback."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    local_called: list[object] = []

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
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


@pytest.mark.sak495_i
def test_sak495_i_tool_run_shell_tools_broker_only_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak495-i: TOOLS=2 — broker failure propagates (no local fallback)."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "2")

    def _boom(*_a, **_k):
        raise RuntimeError("broker_miss: shell_exec: down")

    monkeypatch.setattr("agent_tools.sandbox_bridge.try_broker_sandbox_exec", lambda *_a, **_k: None)
    monkeypatch.setattr("broker_client.stage_bind.tools.try_broker_shell_exec", _boom)
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("local tools")),
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            tool_run_shell(tmp_path, "pytest", ["-q"])


@pytest.mark.sak495_i
def test_sak495_i_tool_run_shell_tools_peel_off_still_falls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak495-i: TOOLS=0 — broker None still allows local/tools fallback."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.delenv("NIMBUSWARE_BROKER_TOOLS", raising=False)
    proc = MagicMock()
    proc.combined_output = "local ok"
    proc.returncode = 0
    proc.backend = "none"

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: proc,
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        result = tool_run_shell(tmp_path, "pytest", ["-q"])

    assert result.ok is True
    assert "local ok" in result.llm_output


def test_sak495_i_source_markers() -> None:
    """sak495-i: TOOLS peel miss wired in production modules."""
    tools_src = (_ROOT / "packages" / "broker_client" / "stage_bind" / "tools.py").read_text(
        encoding="utf-8",
    )
    shell_src = (_ROOT / "packages" / "agent_tools" / "shell_tools.py").read_text(encoding="utf-8")
    bridge_src = (_ROOT / "packages" / "agent_tools" / "sandbox_bridge.py").read_text(
        encoding="utf-8",
    )

    assert "sak495-i" in tools_src
    assert "sak495-i" in shell_src
    assert "raise_tools_peel_miss" in bridge_src


# --- sak495-c: platform analytics + bootstrap + fleet analytics OpenAPI 503 ---

import json

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    analytics_json_openapi_responses,
    enterprise_peel_json_openapi_responses,
    platform_bootstrap_json_openapi_responses,
)

SAK495_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/analytics/stitch-outcomes", "get"),
    ("/v1/platform/analytics/competitive-summary", "get"),
    ("/v1/platform/analytics/pressure-history", "get"),
    ("/v1/platform/analytics/chat-turns", "get"),
    ("/v1/platform/analytics/bundle-outcomes", "get"),
    ("/v1/platform/playwright-bootstrap", "get"),
    ("/v1/platform/playwright-bootstrap", "post"),
    ("/v1/enterprise/fleet/analytics/compare", "get"),
    ("/v1/enterprise/fleet/analytics/tenant/{tenant_id}", "get"),
)


def _sak495_c_openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


def test_sak495_c_openapi_artifact_documents_peel_503() -> None:
    """sak495-c: openapi.json lists 503 problem+json on analytics/bootstrap/fleet paths."""
    spec = json.loads(_sak495_c_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK495_C_PEEL_OPENAPI:
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


def test_sak495_c_peel_routes_source_wire_openapi_helpers() -> None:
    """sak495-c: route sources wire analytics/bootstrap/fleet peel OpenAPI helpers."""
    root = _ROOT / "packages" / "api"
    analytics = (root / "routes" / "analytics.py").read_text(encoding="utf-8")
    platform = (root / "routes" / "platform.py").read_text(encoding="utf-8")
    fleet = (root / "routes" / "enterprise" / "fleet_analytics.py").read_text(encoding="utf-8")
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")

    assert "sak495-c" in peel
    assert analytics_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert platform_bootstrap_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert enterprise_peel_json_openapi_responses()[503] is PROBLEM_RESPONSE_503

    for needle in (
        "/platform/analytics/stitch-outcomes",
        "/platform/analytics/competitive-summary",
        "/platform/analytics/pressure-history",
        "/platform/analytics/chat-turns",
        "/platform/analytics/bundle-outcomes",
    ):
        assert needle in analytics
        assert "responses=analytics_json_openapi_responses" in analytics

    assert "/platform/playwright-bootstrap" in platform
    assert "responses=platform_bootstrap_json_openapi_responses" in platform

    assert "/compare" in fleet and "responses=enterprise_peel_json_openapi_responses" in fleet
    assert "/tenant/{tenant_id}" in fleet
    assert fleet.count("responses=enterprise_peel_json_openapi_responses") >= 2


# --- sak495-d: long-tail peel OpenAPI (admin OAuth, subscription OAuth, bundle catalog) ---

import json

from api.schemas.openapi import PROBLEM_RESPONSE_401, PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    AdminOAuthLogoutMissResponse,
    AdminOAuthSessionMissResponse,
    BundleCatalogSourceMissResponse,
    CatalogCandidatesMissResponse,
    SubscriptionOauthStatusMissResponse,
    long_tail_json_openapi_responses,
)

SAK495_D_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/admin/oauth/session", "get"),
    ("/v1/admin/oauth/logout", "post"),
    ("/v1/platform/provider-subscriptions/oauth/status", "get"),
    ("/v1/bundles/catalog-candidates", "get"),
    ("/v1/bundles/catalog/source", "get"),
)


def _openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


def test_sak495_d_source_markers() -> None:
    """sak495-d: long-tail routes wire long_tail_json_openapi_responses + peel miss schemas."""
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    admin_oauth = (_ROOT / "packages" / "api" / "routes" / "admin_oauth.py").read_text(
        encoding="utf-8",
    )
    sub_oauth = (
        _ROOT / "packages" / "api" / "routes" / "provider_subscription_oauth.py"
    ).read_text(encoding="utf-8")
    bundles = (_ROOT / "packages" / "api" / "routes" / "bundles.py").read_text(encoding="utf-8")

    assert "sak495-d" in peel
    assert "AdminOAuthSessionMissResponse" in peel
    assert "SubscriptionOauthStatusMissResponse" in peel
    assert "CatalogCandidatesMissResponse" in peel
    assert "long_tail_json_openapi_responses" in admin_oauth
    assert "/session" in admin_oauth and "long_tail_json_openapi_responses" in admin_oauth
    assert "/logout" in admin_oauth
    assert "long_tail_json_openapi_responses" in sub_oauth
    assert "/catalog-candidates" in bundles and "long_tail_json_openapi_responses" in bundles
    assert "/catalog/source" in bundles


@pytest.mark.sak495_d
def test_sak495_d_peel_miss_schemas() -> None:
    """sak495-d: peel miss models carry route-shaped defaults."""
    session = AdminOAuthSessionMissResponse(
        via="broker_miss",
        authenticated=False,
        console_role="readonly",
    )
    assert session.via == "broker_miss"

    logout = AdminOAuthLogoutMissResponse(via="broker_miss", ok=False)
    assert logout.ok is False

    sub = SubscriptionOauthStatusMissResponse(via="broker_miss", providers=[])
    assert sub.providers == []

    candidates = CatalogCandidatesMissResponse(via="broker_miss", candidates=[])
    assert candidates.candidates == []

    source = BundleCatalogSourceMissResponse(via="broker_miss", authoritative="yaml")
    assert source.authoritative == "yaml"


@pytest.mark.sak495_d
def test_sak495_d_openapi_helper() -> None:
    """sak495-d: helper attaches PROBLEM_RESPONSE_503 (+ optional 401)."""
    base = long_tail_json_openapi_responses()
    assert base[503] is PROBLEM_RESPONSE_503
    assert 401 not in base

    with_401 = long_tail_json_openapi_responses(unauthorized=PROBLEM_RESPONSE_401)
    assert with_401[401] is PROBLEM_RESPONSE_401


@pytest.mark.sak495_d
def test_sak495_d_openapi_artifact_documents_peel_503() -> None:
    """sak495-d: openapi.json lists 503 problem+json on long-tail peel paths."""
    spec = json.loads(_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK495_D_PEEL_OPENAPI:
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


# --- sak495-e: ui_shared peel-http broker_memory_only ---


def test_sak495_e_source_markers() -> None:
    """sak495-e: shared peel-http maps broker_memory_only 503 to memory peel miss."""
    peel_http = (_ROOT / "packages" / "ui_shared" / "js" / "peel-http.js").read_text(
        encoding="utf-8",
    )
    broker_miss_js = (
        _ROOT / "packages" / "maker_web" / "static" / "js" / "broker_miss.js"
    ).read_text(encoding="utf-8")
    api_client = (_ROOT / "packages" / "maker_web" / "static" / "js" / "api-client.js").read_text(
        encoding="utf-8",
    )

    assert "sak495-e" in peel_http
    assert "BROKER_MEMORY_ONLY" in peel_http
    assert "broker_memory_only" in peel_http or "BROKER_MEMORY_ONLY" in peel_http
    assert "sak495-e" in broker_miss_js
    assert "broker_memory_only" in broker_miss_js
    assert "sak495-e" in api_client


# --- sak495-f: admin isReadPeelMiss / LoginGate ---


def test_sak495_f_source_markers() -> None:
    """sak495-f: admin read-path peel miss via isReadPeelMiss + LoginGate."""
    peel_assert = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8",
    )
    login_gate = (_ROOT / "packages" / "admin_ui" / "src" / "LoginGate.tsx").read_text(
        encoding="utf-8",
    )

    assert "sak495-f" in peel_assert
    assert "isReadPeelMiss" in peel_assert
    assert "isReadPeelMiss" in login_gate
    assert "sak495-f" in login_gate


# --- sak495-g: peel_assert + SDK is_memory_miss ---


def test_sak495_g_source_markers() -> None:
    """sak495-g: assert_memory_ok / is_memory_miss in peel_assert + Python SDK."""
    peel_assert = (_ROOT / "packages" / "broker_client" / "peel_assert.py").read_text(
        encoding="utf-8",
    )
    memory_bind = (_ROOT / "packages" / "broker_client" / "stage_bind" / "memory.py").read_text(
        encoding="utf-8",
    )
    py_client = (
        _ROOT.parent
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")

    assert "sak495-g" in peel_assert
    assert "is_memory_miss" in peel_assert
    assert "assert_memory_ok" in peel_assert
    assert "sak495-g" in memory_bind
    assert "sak495-g" in py_client
    assert "is_memory_miss" in py_client


# --- sak495-j: compute broker_route build_domain_peel_miss ---


@pytest.mark.sak495_j
def test_sak495_j_compute_domain_peel_miss_refactor() -> None:
    """sak495-j: build_domain_peel_miss shared by compute routes (node: None default)."""
    from broker_client.dual_run_route import build_domain_peel_miss
    from compute import broker_route as compute_route

    body = build_domain_peel_miss(
        "down",
        feature="compute_nodes",
        defaults={"node": None},
    )
    assert body["via"] == "broker_miss"
    assert body["status"] == "degraded"
    assert body["feature"] == "compute_nodes"
    assert body["node"] is None
    assert callable(compute_route.map_broker_compute_http_error)

    compute_src = (_ROOT / "packages" / "compute" / "broker_route.py").read_text(encoding="utf-8")
    assert "map_domain_broker_http_miss" in compute_src  # sak499-f
    assert "sak499-f" in compute_src
    assert 'defaults={"node": None}' in compute_src
