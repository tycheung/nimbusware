from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from orchestrator.llm.gate_helpers import execute_agent_evaluator_policy_llm
from orchestrator.runtime_bootstrap import build_runtime_orchestrator
from orchestrator.workflow.agent_evaluator import (
    AgentEvaluatorAutoCreatePersonaBlock,
    AgentEvaluatorWorkflowBlock,
)

_ROOT = Path(__file__).resolve().parents[2]


def _write_min_roles(repo: Path) -> None:
    roles = repo / "configs" / "roles.yaml"
    roles.parent.mkdir(parents=True, exist_ok=True)
    roles.write_text(
        "version: 1\nroles:\n"
        "  - taxonomy_key: planner\n"
        '    role_id: "11111111-1111-4111-8111-111111111101"\n',
        encoding="utf-8",
    )


# --- sak498-a: peel-safe orchestrator bootstrap ---


def test_sak498_a_runtime_bootstrap_source_markers() -> None:
    """sak498-a: bootstrap skips removed memory.factory; wires peel guard."""
    src = (_ROOT / "packages" / "orchestrator" / "runtime_bootstrap.py").read_text(
        encoding="utf-8",
    )
    assert "sak498-a" in src
    assert "resolve_memory_chunk_store_for_bootstrap" in src
    assert "broker_memory_enabled" in src
    assert "build_memory_chunk_store" not in src


@pytest.mark.sak498_a
@pytest.mark.parametrize("memory_flag", ["1", "2"])
def test_sak498_a_bootstrap_skips_memory_factory_under_peel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_flag: str,
) -> None:
    """sak498-a: MEMORY=1|2 never calls build_memory_chunk_store at startup."""
    _write_min_roles(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", memory_flag)

    with (
        patch("memory.peel_factory.build_memory_chunk_store") as mock_factory,
        patch("orchestrator.runtime_bootstrap.RunOrchestrator") as orch_cls,
    ):
        build_runtime_orchestrator(roles_from_db=False, use_materializer_registry=False)

    mock_factory.assert_not_called()
    assert orch_cls.call_args.kwargs.get("memory_chunk_store") is None


@pytest.mark.sak498_a
def test_sak498_a_bootstrap_memory_store_none_without_peel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak498-a: bootstrap passes None (factory removed) when MEMORY peel off."""
    _write_min_roles(tmp_path)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    monkeypatch.delenv("NIMBUSWARE_DATABASE_URL", raising=False)
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)

    with (
        patch("memory.peel_factory.build_memory_chunk_store") as mock_factory,
        patch("orchestrator.runtime_bootstrap.RunOrchestrator") as orch_cls,
    ):
        build_runtime_orchestrator(roles_from_db=False, use_materializer_registry=False)

    mock_factory.assert_not_called()
    assert orch_cls.call_args.kwargs.get("memory_chunk_store") is None


# --- sak498-b: require_local_memory_chunk_store + memory OpenAPI ---


def test_sak498_b_source_markers() -> None:
    """sak498-b: require_local_memory_chunk_store guards build_memory_chunk_store under peel."""
    route = (_ROOT / "packages" / "memory" / "broker_route.py").read_text(encoding="utf-8")
    peel = (_ROOT / "packages" / "api" / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8",
    )
    assert "sak498-b" in route
    assert "require_local_memory_chunk_store" in route
    assert "map_broker_memory_local_refuse" in route
    assert "sak498-b" in peel
    assert "MemoryChunksMissResponse" in peel or "memory_json_openapi_responses" in peel


@pytest.mark.sak498_b
@pytest.mark.parametrize("memory_flag", ["1", "2"])
def test_sak498_b_require_local_memory_chunk_store_peel(
    monkeypatch: pytest.MonkeyPatch,
    memory_flag: str,
) -> None:
    """sak498-b: require_local returns peel miss under MEMORY=1; raises under MEMORY=2."""
    from fastapi import HTTPException

    from memory.broker_route import require_local_memory_chunk_store

    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", memory_flag)
    if memory_flag == "1":
        out = require_local_memory_chunk_store(feature="memory_chunks")
        assert out.get("via") == "broker_miss"
        return
    with pytest.raises(HTTPException) as ei:
        require_local_memory_chunk_store(feature="memory_chunks")
    assert ei.value.status_code == 503


# --- sak498-d: agent evaluator policy LLM delegate ---


def test_sak498_d_source_markers() -> None:
    """sak498-d: agent_evaluator policy delegate uses chat_facade peel_strict."""
    delegate = (_ROOT / "packages" / "orchestrator" / "llm" / "gate_helpers.py").read_text(
        encoding="utf-8",
    )
    emit = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "agent_evaluator_policy_llm_emit.py"
    ).read_text(encoding="utf-8")
    llm_init = (_ROOT / "packages" / "orchestrator" / "llm" / "__init__.py").read_text(
        encoding="utf-8",
    )

    assert "sak498-d" in delegate
    assert "peel_strict=True" in delegate
    assert "broker_miss: agent_evaluator_policy" in delegate
    assert "execute_agent_evaluator_policy_llm" in delegate
    assert "sak498-d" in emit
    assert "broker_miss: agent_evaluator_policy_llm_emit" in emit
    assert "execute_agent_evaluator_policy_llm" in llm_init
    assert "from orchestrator.llm.gate_helpers import" in llm_init
    assert "execute_agent_evaluator_policy_llm = _removed" not in llm_init


def test_sak498_d_peel_broker_miss_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-d: LLM=1 — broker miss propagates for policy delegate."""
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("broker_miss: chat_facade: down"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_agent_evaluator_policy_llm(
                store,
                reg,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                rules_eval={"status": "ok", "gaps": []},
                persona_id="commerce",
                timeout_seconds=1.0,
            )


def test_sak498_d_peel_invalid_llm_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-d: LLM=1 — invalid LLM payload raises broker_miss (no silent None)."""
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        return_value={"status": "", "gaps": "not-a-list", "summary": 1},
    ):
        with pytest.raises(RuntimeError, match="broker_miss: agent_evaluator_policy"):
            execute_agent_evaluator_policy_llm(
                store,
                reg,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                rules_eval={"status": "ok", "gaps": []},
                persona_id="commerce",
                timeout_seconds=1.0,
            )


def test_sak498_d_non_peel_invalid_llm_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-d: LLM off peel — invalid payload returns None (stub path allowed)."""
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        return_value={"status": "", "gaps": "not-a-list", "summary": 1},
    ):
        out = execute_agent_evaluator_policy_llm(
            store,
            reg,
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            rules_eval={"status": "ok", "gaps": []},
            persona_id="commerce",
            timeout_seconds=1.0,
        )
    assert out is None


def test_sak498_d_peel_strict_passed_to_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-d: policy delegate calls chat_facade with peel_strict=True."""
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> dict[str, str]:
        captured.update(kwargs)
        return {"status": "ok", "gaps": [], "summary": "looks fine"}

    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=_capture,
    ):
        out = execute_agent_evaluator_policy_llm(
            store,
            reg,
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            rules_eval={"status": "ok", "gaps": []},
            persona_id="commerce",
            timeout_seconds=1.0,
        )
    assert out == {"status": "ok", "gaps": [], "summary": "looks fine"}
    assert captured.get("peel_strict") is True
    assert captured.get("stage_name") == "agent_evaluator.policy"


def test_sak498_d_emit_peel_on_llm_none_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-d: emit path refuses stub/rules fallback when delegate returns None under peel."""
    from orchestrator._pipeline.agent_evaluator_policy_llm_emit import (
        resolve_agent_evaluator_policy_llm_for_host,
    )

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


# --- sak498-c: self_refinement critique broker chat + peel_strict ---


def test_sak498_c_source_markers() -> None:
    """sak498-c: self_refinement critique wired via bind_post_verify_role_critique."""
    gate_helpers = (_ROOT / "packages" / "orchestrator" / "llm" / "gate_helpers.py").read_text(
        encoding="utf-8"
    )
    bindings = (
        _ROOT / "packages" / "orchestrator" / "llm" / "post_verify_role_bindings.py"
    ).read_text(encoding="utf-8")
    init = (_ROOT / "packages" / "orchestrator" / "llm" / "__init__.py").read_text(
        encoding="utf-8",
    )
    sr_emit = (
        _ROOT / "packages" / "orchestrator" / "_pipeline" / "self_refinement_critique_emit.py"
    ).read_text(encoding="utf-8")

    assert "sak498-c" in gate_helpers
    assert "execute_self_refinement_critique_llm" in gate_helpers
    assert "peel_strict=True" in gate_helpers.split("execute_self_refinement_critique_llm")[1]
    assert "broker_miss: self_refinement_critique" in gate_helpers
    assert "self_refinement=True" in bindings
    assert "stub_only" not in bindings
    assert "execute_self_refinement_critique_llm" in bindings
    assert "execute_self_refinement_critique_llm = _removed" not in init
    assert "execute_self_refinement_critique_llm" in init
    assert "sak498-c" in sr_emit


def test_sak498_c_peel_broker_miss_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-c: LLM=1 — broker miss propagates for self_refinement critique."""
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm import execute_self_refinement_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("broker_miss: chat_facade: down"),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_self_refinement_critique_llm(
                store,
                reg,
                router,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                evaluation_status="gap",
                gaps=["depth"],
                description="policy text",
                timeout_seconds=1.0,
            )
    assert not store.list_run_events(str(run_id))


def test_sak498_c_peel_invalid_llm_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-c: LLM=1 — invalid LLM payload raises (no silent None)."""
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm import execute_self_refinement_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        return_value=[],
    ):
        with pytest.raises(RuntimeError, match="broker_miss: self_refinement_critique"):
            execute_self_refinement_critique_llm(
                store,
                reg,
                router,
                run_id=run_id,
                base_url="http://127.0.0.1:1",
                model_id="m",
                evaluation_status="gap",
                gaps=["depth"],
                description="policy text",
                timeout_seconds=1.0,
            )


def test_sak498_c_non_peel_invalid_llm_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-c: LLM off peel — invalid payload returns None (stub path allowed)."""
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm import execute_self_refinement_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        return_value=[],
    ):
        out = execute_self_refinement_critique_llm(
            store,
            reg,
            router,
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            evaluation_status="gap",
            gaps=["depth"],
            description="policy text",
            timeout_seconds=1.0,
        )
    assert out is None
    assert not store.list_run_events(str(run_id))


def test_sak498_c_peel_strict_passed_to_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-c: self_refinement critique calls chat_facade with peel_strict=True."""
    from extensions.extension_runtime import UniversalCritiqueRouter
    from orchestrator.llm import execute_self_refinement_critique_llm
    from orchestrator.registry import RoleRegistry
    from store.memory import InMemoryEventStore

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    reg = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    captured: dict[str, Any] = {}

    def _capture(**kwargs: Any) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "verdict": "PASS",
            "gate_decision": "proceed",
            "summary": "minor gaps only",
        }

    with patch(
        "orchestrator.llm.gate_helpers.ollama_chat_json_via_plan_patch",
        side_effect=_capture,
    ):
        out = execute_self_refinement_critique_llm(
            store,
            reg,
            router,
            run_id=run_id,
            base_url="http://127.0.0.1:1",
            model_id="m",
            evaluation_status="gap",
            gaps=["depth"],
            description="policy text",
            timeout_seconds=1.0,
        )
    assert out == {
        "verdict": "PASS",
        "gate_decision": "proceed",
        "summary": "minor gaps only",
    }
    assert captured.get("peel_strict") is True
    assert captured.get("stage_name") == "self_refinement.critique"
    rows = store.list_run_events(str(run_id))
    assert any(r.get("event_type") == "gate.decision.emitted" for r in rows)


def test_sak498_c_emit_host_uses_wired_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-c: emit path consumes broker-wired execute result dict."""
    from orchestrator._pipeline.self_refinement_critique_emit import (
        try_emit_self_refinement_critique_for_host,
    )

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
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
            return_value={
                "verdict": "PASS",
                "gate_decision": "proceed",
                "summary": "ready",
            },
        ),
    ):
        out = try_emit_self_refinement_critique_for_host(
            host,
            uuid4(),
            llm_critique_enabled=True,
            gate_decision="hold",
            workflow_profile="nimbusware_production",
            workflow_block=object(),
            evaluation_status="gap",
            gaps=["depth"],
            description="policy text",
        )
    assert out.get("orchestration_branch") == "rules_with_llm_critique"
    assert out.get("llm_critique_verdict") == "PASS"
    assert out.get("llm_gate_decision") == "proceed"


# --- sak498-e: OpenAPI 503 long-tail — context_artifacts, ollama, dev_env, web bootstrap ---


import json

from api.schemas.openapi import PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    ContextArtifactFromCompactionMissResponse,
    ContextArtifactInsertMissResponse,
    llm_json_openapi_responses,
    memory_json_openapi_responses,
    runs_json_openapi_responses,
)

SAK498_E_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/runs/{run_id}/context-artifacts/from-compaction", "post"),
    ("/v1/runs/{run_id}/context-artifacts/{artifact_id}/insert", "post"),
    ("/v1/platform/ollama/models", "get"),
    ("/v1/platform/ollama/bootstrap", "post"),
    ("/v1/platform/ollama/pull", "post"),
    ("/v1/platform/ollama/pull/{job_id}", "get"),
    ("/v1/platform/ollama/models/{model_name}", "delete"),
    ("/v1/platform/ollama/routing/primary", "patch"),
    ("/v1/admin/ollama/user-policy", "patch"),
    ("/v1/admin/ollama/pull", "post"),
    ("/v1/admin/ollama/models/{model_name}", "delete"),
    ("/v1/runs/{run_id}/dev-env/status", "get"),
    ("/v1/runs/{run_id}/dev-env/start", "post"),
    ("/v1/runs/{run_id}/dev-env/stop", "post"),
    ("/v1/runs/{run_id}/dev-env/regression", "post"),
    ("/v1/runs/{run_id}/dev-env/ui-regression", "post"),
    ("/v1/runs/{run_id}/dev-env/theater", "get"),
)


def _sak498_e_openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


@pytest.mark.sak498_e
def test_sak498_e_openapi_artifact_documents_peel_503() -> None:
    """sak498-e: openapi.json lists 503 problem+json on long-tail peel paths."""
    spec = json.loads(_sak498_e_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK498_E_PEEL_OPENAPI:
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


@pytest.mark.sak498_e
def test_sak498_e_peel_routes_source_wire_openapi_helpers() -> None:
    """sak498-e: context_artifacts, ollama, dev_env wire peel OpenAPI helpers."""
    root = _ROOT / "packages" / "api"
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    context = (root / "routes" / "runs" / "context_artifacts.py").read_text(encoding="utf-8")
    ollama = (root / "routes" / "ollama.py").read_text(encoding="utf-8")
    dev_env = (root / "routes" / "runs" / "dev_env.py").read_text(encoding="utf-8")
    web_bootstrap = (root / "routes" / "web_bootstrap.py").read_text(encoding="utf-8")
    ollama_schemas = (root / "schemas" / "ollama.py").read_text(encoding="utf-8")

    assert "sak498-e" in peel
    assert memory_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert llm_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert runs_json_openapi_responses(not_found={"x": 1})[404] == {"x": 1}
    assert ContextArtifactFromCompactionMissResponse().via is None
    assert ContextArtifactInsertMissResponse().via is None

    assert context.count("memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)") == 2
    assert "sak498-e" in context

    assert ollama.count("llm_json_openapi_responses") >= 9
    assert "sak498-e" in ollama

    assert dev_env.count("runs_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)") >= 6
    assert "sak498-e" in dev_env
    assert "status: str | None = None" in dev_env

    assert "status: str | None = None  # sak498-e" in web_bootstrap

    assert ollama_schemas.count("status: str | None = None  # sak498-e") >= 5


# --- sak498-i: soft-swallow close (lifecycle/test_writer/faiss) ---


def test_sak498_i_source_markers() -> None:
    """sak498-i: lifecycle/test_writer narrow soft-swallow; faiss rebuild raises under MEMORY peel."""
    lifecycle = (_ROOT / "packages" / "orchestrator" / "_pipeline" / "lifecycle_plan.py").read_text(
        encoding="utf-8"
    )
    tw = (_ROOT / "packages" / "orchestrator" / "test_writer_stage.py").read_text(
        encoding="utf-8",
    )
    ctx = (_ROOT / "packages" / "orchestrator" / "context_artifacts.py").read_text(
        encoding="utf-8",
    )
    assert "sak498-i" in lifecycle
    assert "_llm_broker_miss_or_transport" in lifecycle
    assert "sak498-i" in tw
    assert "_llm_broker_miss_or_transport" in tw
    assert "sak498-i" in ctx
    assert "refuse_legacy" in ctx


def test_sak498_i_lifecycle_peel_off_broker_miss_stub_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-i: LLM=0 — broker_miss still soft-falls back to plan stub."""
    from collections.abc import Iterator
    from contextlib import contextmanager
    from uuid import uuid4

    from orchestrator.pipeline import make_dev_orchestrator

    @contextmanager
    def _patched_plan_stage(orch: Any) -> Iterator[MagicMock]:
        with (
            patch.object(orch, "_maybe_emit_research_stages"),
            patch.object(orch, "_maybe_emit_stitch_stages"),
            patch.object(orch, "_run_created_metadata", return_value={}),
            patch(
                "research.reresearch.maybe_reresearch_after_plan_fail",
                return_value=False,
            ),
            patch.object(orch, "_selected_model_for_run", return_value="dev:primary"),
            patch(
                "orchestrator._pipeline.lifecycle_plan.execute_plan_stage_llm",
                side_effect=RuntimeError("broker_miss: chat_facade: down"),
            ),
            patch(
                "orchestrator._pipeline.lifecycle_plan.emit_stub_plan_stage",
            ) as mock_stub,
        ):
            yield mock_stub

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(orch) as mock_stub:
        orch.execute_plan_stage(run_id)
    mock_stub.assert_called_once()


def test_sak498_i_lifecycle_peel_off_non_broker_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-i: LLM=0 — non-broker RuntimeError propagates (no stub fallback)."""
    from collections.abc import Iterator
    from contextlib import contextmanager
    from uuid import uuid4

    from orchestrator.pipeline import make_dev_orchestrator

    @contextmanager
    def _patched_plan_stage(orch: Any) -> Iterator[tuple[MagicMock, MagicMock]]:
        with (
            patch.object(orch, "_maybe_emit_research_stages"),
            patch.object(orch, "_maybe_emit_stitch_stages"),
            patch.object(orch, "_run_created_metadata", return_value={}),
            patch(
                "research.reresearch.maybe_reresearch_after_plan_fail",
                return_value=False,
            ),
            patch.object(orch, "_selected_model_for_run", return_value="dev:primary"),
            patch(
                "orchestrator._pipeline.lifecycle_plan.execute_plan_stage_llm",
                side_effect=RuntimeError("invalid plan panel"),
            ) as mock_llm,
            patch(
                "orchestrator._pipeline.lifecycle_plan.emit_stub_plan_stage",
            ) as mock_stub,
        ):
            yield mock_llm, mock_stub

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    orch, _store = make_dev_orchestrator()
    run_id = uuid4()

    with _patched_plan_stage(orch) as (_mock_llm, mock_stub):
        with pytest.raises(RuntimeError, match="invalid plan panel"):
            orch.execute_plan_stage(run_id)
    mock_stub.assert_not_called()


def test_sak498_i_test_writer_peel_off_broker_miss_soft_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-i: LLM=0 — broker_miss soft-returns error tuple (does not raise)."""
    from orchestrator.test_writer_stage import run_test_writer_stage

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")

    with patch(
        "orchestrator.test_writer_stage.ollama_chat_json_via_plan_patch",
        side_effect=RuntimeError("broker_miss: test_writer: down"),
    ):
        code, out, mode = run_test_writer_stage(
            Path("."),
            llm_body_enabled=True,
            llm_stub_fallback=False,
            llm_model_id="m",
        )
    assert code == 1
    assert mode == "llm"
    assert "broker_miss" in out


def test_sak498_i_test_writer_peel_off_value_error_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-i: LLM=0 — non-transport ValueError propagates."""
    from orchestrator.test_writer_stage import run_test_writer_stage

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
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


@pytest.mark.parametrize("memory_flag", ["1", "2"])
def test_sak498_i_faiss_rebuild_raises_under_memory_peel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    memory_flag: str,
) -> None:
    """sak498-i: FAISS rebuild env set + MEMORY=1|2 raises (no silent None)."""
    from orchestrator.context_artifacts import maybe_rebuild_memory_faiss_from_bridges

    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", memory_flag)
    monkeypatch.setenv("NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD", "1")
    bridge_dir = tmp_path / ".cache" / "nimbusware" / "memory-bridge" / "proj"
    bridge_dir.mkdir(parents=True)
    (bridge_dir / "a.json").write_text(
        '{"artifact_id":"a","title":"t","excerpt":"hello bridge"}',
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="MEMORY=1\\|2"):
        maybe_rebuild_memory_faiss_from_bridges("proj", repo_root=tmp_path)


# --- sak498-f: Maker high-traffic tab domain peel miss consolidation ---


def test_sak498_f_maker_tab_domain_peel_miss_markers() -> None:
    """sak498-f: high-traffic Maker tabs use isDomainPeelMiss + formatDomainMissMessage."""
    js = _ROOT / "packages" / "maker_web" / "static" / "js"
    broker_miss = (js / "broker_miss.js").read_text(encoding="utf-8")
    assert "sak498-f" in broker_miss
    assert "isDomainPeelMiss(body) || isCapacityMiss(body)" in broker_miss
    for name in ("home.js", "progress.js", "settings.js", "review.js", "chat_model_drawer_ui.js"):
        src = (js / "tabs" / name).read_text(encoding="utf-8")
        assert "sak498-f" in src
        assert "isDomainPeelMiss" in src
        assert "isBrokerMiss" not in src
        if name in ("home.js", "progress.js", "chat_model_drawer_ui.js"):
            assert "formatDomainMissMessage" in src
            assert "missBannerText" not in src


# --- sak498-g: BrokerClient domain MCP helpers (assert_sandbox_ok / assert_llm_ok) ---


def test_sak498_g_source_markers() -> None:
    """sak498-g: BrokerClient + stage_bind wire domain peel asserts."""
    client = (_ROOT / "packages" / "broker_client" / "client.py").read_text(encoding="utf-8")
    peel = (_ROOT / "packages" / "broker_client" / "peel_assert.py").read_text(encoding="utf-8")
    sandbox = (_ROOT / "packages" / "broker_client" / "stage_bind" / "sandbox.py").read_text(
        encoding="utf-8",
    )
    llm = (_ROOT / "packages" / "broker_client" / "stage_bind" / "llm.py").read_text(
        encoding="utf-8",
    )
    assert client.count("sak498-g") >= 5
    assert "assert_sandbox_ok" in client
    assert "assert_llm_ok" in client
    assert "normalize_tool_result" in peel
    assert "sak498-g" in peel
    assert "assert_sandbox_ok" in peel
    assert "assert_llm_ok" in peel
    assert "sak498-g" in sandbox
    assert "sak498-g" in llm


@pytest.mark.sak498_g
def test_sak498_g_assert_sandbox_ok_raises_on_miss() -> None:
    """sak498-g: assert_sandbox_ok raises RuntimeError on peel miss dict."""
    from broker_client.peel_assert import assert_sandbox_ok

    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_sandbox_ok(
            {"via": "broker_miss", "error": "down", "feature": "sandbox_exec"},
            feature="sandbox_exec",
        )
    assert assert_sandbox_ok({"stdout": "ok"}, feature="sandbox_exec") == {"stdout": "ok"}


@pytest.mark.sak498_g
def test_sak498_g_assert_llm_ok_raises_on_miss() -> None:
    """sak498-g: assert_llm_ok raises RuntimeError on peel miss dict."""
    from broker_client.peel_assert import assert_llm_ok

    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_llm_ok(
            {"via": "broker_miss", "error": "down", "feature": "llm_chat"},
            feature="llm_chat",
        )
    assert assert_llm_ok({"content": "ok"}, feature="llm_chat") == {"content": "ok"}


# --- sak498-h: fleet-memory resolve_memory_store_or_miss consolidation ---


def test_sak498_h_source_markers() -> None:
    """sak498-h: fleet-memory routes use shared resolve_memory_store_or_miss helper."""
    route = (_ROOT / "packages" / "memory" / "broker_route.py").read_text(encoding="utf-8")
    fleet = (_ROOT / "packages" / "api" / "routes" / "enterprise" / "fleet_memory.py").read_text(
        encoding="utf-8",
    )
    peel = (_ROOT / "packages" / "broker_client" / "peel_assert.py").read_text(encoding="utf-8")
    assert "sak498-h" in route
    assert "resolve_memory_store_or_miss" in route
    assert "is_memory_store_or_miss" in peel
    assert "sak498-h" in peel
    assert "resolve_memory_store_or_miss" in fleet
    assert "build_memory_chunk_store" not in fleet
    assert "map_broker_memory_local_refuse" not in fleet


@pytest.mark.parametrize("memory_flag", ["1", "2"])
def test_sak498_h_resolve_memory_store_or_miss_peel(
    monkeypatch: pytest.MonkeyPatch,
    memory_flag: str,
) -> None:
    """sak498-h: resolve returns peel miss under MEMORY=1; raises 503 under MEMORY=2."""
    from fastapi import HTTPException

    from memory.broker_route import resolve_memory_store_or_miss

    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", memory_flag)
    if memory_flag == "1":
        out = resolve_memory_store_or_miss(
            feature="fleet_memory_rebuild",
            miss_extra={"tenant_id": "t1"},
        )
        assert out.get("via") == "broker_miss"
        assert out.get("feature") == "fleet_memory_rebuild"
        assert out.get("tenant_id") == "t1"
        return
    with pytest.raises(HTTPException) as ei:
        resolve_memory_store_or_miss(
            feature="fleet_memory_rebuild",
            miss_extra={"tenant_id": "t1"},
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_sak498_h_resolve_local_only_raises_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak498-h: local_only raises memory_store_unavailable when store is None."""
    from fastapi import HTTPException

    from memory.broker_route import resolve_memory_store_or_miss

    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)
    with (
        patch("memory.broker_route.build_memory_chunk_store", return_value=None),
        pytest.raises(HTTPException) as ei,
    ):
        resolve_memory_store_or_miss(feature="fleet_memory_search", local_only=True)
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "memory_store_unavailable"


def test_sak498_h_is_memory_store_or_miss() -> None:
    """sak498-h: peel_assert detects resolve peel miss dicts."""
    from broker_client.peel_assert import is_memory_store_or_miss

    assert is_memory_store_or_miss(
        {"via": "broker_miss", "feature": "fleet_memory_sync", "error": "down"},
    )
    assert not is_memory_store_or_miss({"hits": []})
    assert not is_memory_store_or_miss(None)


# --- sak498-j: soak/CI close-out (peel_soak_lib + workflow wiring) ---


def test_sak498_j_soak_lib_asserts_present() -> None:
    """sak498-j: peel_soak_lib wires bootstrap/memory/LLM/MCP close-out asserts."""
    soak = (_ROOT / "scripts" / "peel_soak_lib.py").read_text(encoding="utf-8")
    assert "_assert_sak498_bootstrap_resolve_memory" in soak
    assert "_assert_sak498_require_local_memory" in soak
    assert "_assert_sak498_llm_exports_not_removed" in soak
    assert "_assert_sak498_domain_assert_llm_ok" in soak
    assert "sak498 bootstrap resolve_memory" in soak
    assert 'label.startswith("sak498")' in soak
    assert "sak498-j — bootstrap/memory harden" in soak


@pytest.mark.sak498_j
def test_sak498_j_ci_workflow_lists_peel_unit() -> None:
    """sak498-j: nimbusware-peel.yml includes test_sak498_peel.py in peel-unit bundle."""
    workflow = (_ROOT.parent / ".github" / "workflows" / "nimbusware-peel.yml").read_text(
        encoding="utf-8"
    )
    assert "test_sak498_peel.py" in workflow
