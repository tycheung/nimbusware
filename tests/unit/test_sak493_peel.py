from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    FleetMemorySearchMissResponse,
    IntentClassifierMissResponse,
    LlmPeelMissResponse,
    MemoryPeelMissResponse,
    capacity_json_openapi_responses,
    compute_json_openapi_responses,
    llm_json_openapi_responses,
    memory_json_openapi_responses,
)
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique.handlers import execute_security_critique_llm
from orchestrator.launch.launch_test_llm import generate_llm_ui_flow_dict
from orchestrator.persona.coverage_critique import execute_persona_coverage_critique_llm
from orchestrator.refactor_stage import emit_refactor_stage_and_critique
from orchestrator.registry import RoleRegistry
from orchestrator.workflow.refactor import RefactorWorkflowBlock
from orchestrator.workflow.scan_critique import SecurityCritiqueBlock
from store.memory import InMemoryEventStore

_ROOT = Path(__file__).resolve().parents[2]


def test_llm_peel_miss_schema() -> None:
    """sak493-b: LLM peel miss model carries via/broker_miss/status/feature."""
    base = LlmPeelMissResponse(
        via="broker_miss",
        status="degraded",
        feature="intent_classifier",
        error="down",
    )
    assert base.via == "broker_miss"
    assert base.status == "degraded"


def test_intent_classifier_miss_schema() -> None:
    """sak493-b: classify peel miss includes empty classification payload."""
    miss = IntentClassifierMissResponse(
        via="broker_miss",
        status="degraded",
        feature="intent_classifier",
        error="down",
        classification={},
    )
    assert miss.classification == {}


def test_llm_json_openapi_responses_helper() -> None:
    """sak493-b: helper attaches PROBLEM_RESPONSE_503 (+ optional 404)."""
    base = llm_json_openapi_responses()
    assert base[503] is PROBLEM_RESPONSE_503
    assert 404 not in base

    with_404 = llm_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)
    assert with_404[404] is PROBLEM_RESPONSE_404


def test_classify_route_wires_llm_openapi_responses() -> None:
    """sak493-b: POST /chat/classify wires llm_json_openapi_responses."""
    root = _ROOT / "packages" / "api"
    chat = (root / "routes" / "chat.py").read_text(encoding="utf-8")
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")

    assert "sak493-b" in peel
    assert "LlmPeelMissResponse" in peel
    assert "IntentClassifierMissResponse" in peel
    assert "llm_json_openapi_responses" in chat
    assert "/classify" in chat and "responses=llm_json_openapi_responses" in chat


def test_sak493_e_refactor_stage_peel_wiring() -> None:
    """sak493-e: refactor stage stops Exception soft fallback under LLM peel."""
    refactor = (_ROOT / "packages" / "orchestrator" / "refactor_stage.py").read_text(
        encoding="utf-8"
    )
    assert "sak493-e" in refactor
    assert "broker_llm_enabled" in refactor


def test_sak493_e_refactor_stage_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak493-e: refactor LLM peel on — broker_miss propagates (no code_intel fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "orphan.py").write_text("X = 1\n", encoding="utf-8")

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: refactor_stage: broker down")

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    run_id = uuid4()

    with patch(
        "orchestrator.llm.chat_facade.ollama_chat_json_via_plan_patch",
        side_effect=_broker_miss,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
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


def test_sak493_e_refactor_stage_peel_off_broker_miss_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak493-e: LLM=0 — broker_miss still soft-falls back to code_intel_proposal."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "orphan.py").write_text("X = 1\n", encoding="utf-8")

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: refactor_stage: broker down")

    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    run_id = uuid4()

    with (
        patch(
            "orchestrator.llm.chat_facade.ollama_chat_json_via_plan_patch",
            side_effect=_broker_miss,
        ),
        patch("orchestrator.refactor_stage.append_gate_decision_event"),
    ):
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


def test_sak493_d_peel_strict_wiring() -> None:
    """sak493-d: remaining orchestrator LLM callers wire peel_strict + broker_miss."""
    root = _ROOT / "packages" / "orchestrator"
    persona = (root / "persona" / "critique_llm.py").read_text(encoding="utf-8")
    launch = (root / "launch" / "launch_test_llm.py").read_text(encoding="utf-8")
    scan = (root / "critique" / "llm.py").read_text(encoding="utf-8")

    assert "sak493-d" in persona
    assert "peel_strict=True" in persona
    assert "broker_miss" in persona
    assert "sak493-d" in launch
    assert "peel_strict=True" in launch
    assert "broker_miss" in launch
    assert "sak493-d" in scan
    assert "peel_strict=True" in scan
    assert "broker_miss" in scan


def test_sak493_d_persona_critique_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak493-d: persona rules critique LLM peel on — broker_miss propagates."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: persona_critique_llm: broker down")

    with patch(
        "orchestrator.persona.critique_llm.ollama_chat_json_via_plan_patch",
        side_effect=_broker_miss,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_persona_coverage_critique_llm(
                store,
                registry,
                router,
                run_id=run_id,
                rules_eval={"status": "ok", "gaps": []},
                base_url="http://127.0.0.1:1",
                model_id="m",
                timeout_seconds=1.0,
            )
    assert not store.list_run_events(str(run_id))


def test_sak493_d_launch_test_llm_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak493-d: launch test LLM peel on — broker_miss propagates (no None fallback)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_DEFAULT_MODEL", "m")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "README.md").write_text("demo", encoding="utf-8")

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: launch_test_llm: broker down")

    with patch(
        "orchestrator.launch.launch_test_llm.ollama_chat_json_via_plan_patch",
        side_effect=_broker_miss,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            generate_llm_ui_flow_dict(ws)


def test_sak493_d_scan_critique_peel_strict_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak493-d: scan critique LLM peel_strict — broker_miss propagates under LLM=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    block = SecurityCritiqueBlock(severity_floor="medium")

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: scan_critique_llm: broker down")

    with patch(
        "orchestrator.critique.llm.ollama_chat_json_via_plan_patch",
        side_effect=_broker_miss,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            execute_security_critique_llm(
                store,
                registry,
                router,
                run_id=run_id,
                scan_summary={"security_scan_tools": {}},
                base_url="http://127.0.0.1:1",
                model_id="m",
                block=block,
                timeout_seconds=1.0,
            )
    assert not store.list_run_events(str(run_id))


# sak493-c: checked-in Admin OpenAPI artifact + CI assertions (app.openapi() may be broken).
SAK493_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/compute/work-units/enqueue", "post"),
    ("/v1/compute/work-units/claim", "post"),
    ("/v1/compute/nodes/register", "post"),
    ("/v1/compute/nodes/{node_id}/heartbeat", "post"),
    ("/v1/compute/work-units/{work_unit_id}/terminate-restart", "post"),
    ("/v1/compute/work-units/{work_unit_id}/complete", "post"),
    ("/v1/platform/readiness", "get"),
    ("/v1/chat/classify", "post"),
)


def _openapi_json_path() -> Path:
    return _ROOT / "packages" / "admin_ui" / "src" / "api" / "openapi.json"


def test_sak493_c_openapi_artifact_documents_peel_503() -> None:
    """sak493-c: openapi.json lists 503 problem+json on COMPUTE=2 POST + readiness/classify."""
    spec = json.loads(_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK493_C_PEEL_OPENAPI:
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


def test_sak493_c_peel_routes_source_wire_openapi_helpers() -> None:
    """sak493-c: route sources wire compute/capacity/llm peel OpenAPI helpers."""
    root = _ROOT / "packages" / "api"
    compute = (root / "routes" / "compute.py").read_text(encoding="utf-8")
    platform = (root / "routes" / "platform.py").read_text(encoding="utf-8")
    chat = (root / "routes" / "chat.py").read_text(encoding="utf-8")
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")

    assert "sak493-c" in peel
    assert compute_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert capacity_json_openapi_responses()[503] is PROBLEM_RESPONSE_503
    assert llm_json_openapi_responses()[503] is PROBLEM_RESPONSE_503

    for needle in (
        "/compute/work-units/enqueue",
        "/compute/work-units/claim",
        "/compute/nodes/register",
        "/compute/nodes/{node_id}/heartbeat",
        "/compute/work-units/{work_unit_id}/terminate-restart",
        "/compute/work-units/{work_unit_id}/complete",
    ):
        assert needle in compute
        assert "responses=compute_json_openapi_responses" in compute

    assert "/platform/readiness" in platform
    assert "responses=capacity_json_openapi_responses" in platform
    assert "/classify" in chat and "responses=llm_json_openapi_responses" in chat


def test_memory_peel_miss_schema() -> None:
    """sak493-i: memory peel miss model carries via/broker_miss/status/feature."""
    base = MemoryPeelMissResponse(
        via="broker_miss",
        status="degraded",
        feature="fleet_memory_search",
        error="down",
    )
    assert base.via == "broker_miss"
    assert base.status == "degraded"


def test_fleet_memory_search_miss_schema() -> None:
    """sak493-i: fleet memory search peel miss includes empty hits payload."""
    miss = FleetMemorySearchMissResponse(
        via="broker_miss",
        status="degraded",
        feature="fleet_memory_search",
        error="down",
        query="q",
        hits=[],
        hit_count=0,
    )
    assert miss.hits == []
    assert miss.query == "q"


def test_memory_json_openapi_responses_helper() -> None:
    """sak493-i: helper attaches PROBLEM_RESPONSE_503 (+ optional 404)."""
    base = memory_json_openapi_responses()
    assert base[503] is PROBLEM_RESPONSE_503
    assert 404 not in base

    with_404 = memory_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)
    assert with_404[404] is PROBLEM_RESPONSE_404


def test_fleet_memory_routes_wire_memory_openapi() -> None:
    """sak493-i: fleet-memory status/search wire memory_json_openapi_responses."""
    root = _ROOT / "packages" / "api"
    fleet = (root / "routes" / "enterprise" / "fleet_memory.py").read_text(encoding="utf-8")
    peel = (root / "schemas" / "peel_responses.py").read_text(encoding="utf-8")
    admin_peel = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8"
    )
    fleet_page = (_ROOT / "packages" / "admin_ui" / "src" / "pages" / "FleetPage.tsx").read_text(
        encoding="utf-8"
    )

    assert "sak493-i" in peel
    assert "MemoryPeelMissResponse" in peel
    assert "FleetMemorySearchMissResponse" in peel
    assert "memory_json_openapi_responses" in fleet
    assert "try_broker_memory_search" in fleet
    assert "/status" in fleet and "responses=memory_json_openapi_responses" in fleet
    assert "/search" in fleet and "responses=memory_json_openapi_responses" in fleet
    assert "broker_memory_only" in admin_peel
    assert "isMemoryMiss" in fleet_page
    assert "peelMissFromFetchError" in fleet_page


SAK493_I_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/enterprise/fleet-memory/status", "get"),
    ("/v1/enterprise/fleet-memory/search", "get"),
)


def test_sak493_i_openapi_artifact_documents_memory_503() -> None:
    """sak493-i: openapi.json lists 503 problem+json on fleet-memory peel paths."""
    spec = json.loads(_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK493_I_PEEL_OPENAPI:
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


def test_sak493_i_memory_broker_flags_api_module() -> None:
    """sak493-i: MEMORY=1|2 matrix covers fleet-memory search/status."""
    flags = (_ROOT / "tests" / "api_http" / "test_memory_broker_flags_api.py").read_text(
        encoding="utf-8"
    )
    assert "sak493-i" in flags
    assert "test_search_under_memory_1_broker_miss" in flags
    assert "test_search_under_memory_2_returns_503" in flags
    assert "test_status_under_memory_1_broker_miss" in flags
    assert "test_status_under_memory_2_returns_503" in flags


def test_sak493_a_platform_readiness_openapi() -> None:
    """sak493-a: readiness wires capacity OpenAPI helper."""
    from api.schemas.peel_responses import PlatformReadinessPeelMissResponse

    miss = PlatformReadinessPeelMissResponse(via="broker_miss", status="degraded", checks={})
    assert miss.via == "broker_miss"
    platform = (_ROOT / "packages" / "api" / "routes" / "platform.py").read_text(encoding="utf-8")
    assert "sak493-a" in platform
    assert "capacity_json_openapi_responses" in platform
    assert "/platform/readiness" in platform


def test_sak493_f_ui_shared_503_peel_map() -> None:
    """sak493-f: ui_shared + Maker mapHttp503PeelMiss."""
    peel_http = (_ROOT / "packages" / "ui_shared" / "js" / "peel-http.js").read_text(
        encoding="utf-8"
    )
    api_client = (_ROOT / "packages" / "maker_web" / "static" / "js" / "api-client.js").read_text(
        encoding="utf-8"
    )
    broker_miss = (_ROOT / "packages" / "maker_web" / "static" / "js" / "broker_miss.js").read_text(
        encoding="utf-8"
    )
    assert "sak493-f" in peel_http or "mapHttp503PeelMiss" in peel_http
    assert "mapHttp503PeelMiss" in peel_http
    assert "mapHttp503PeelMiss" in api_client
    assert "broker_llm_unavailable" in peel_http or "broker_llm_unavailable" in broker_miss


def test_sak493_g_admin_use_api_get_parity() -> None:
    """sak493-g: admin formatReadCatchMessage + useApiGet catch parity."""
    peel = (_ROOT / "packages" / "admin_ui" / "src" / "api" / "peel_assert.ts").read_text(
        encoding="utf-8"
    )
    hook = (_ROOT / "packages" / "admin_ui" / "src" / "hooks" / "useApiGet.ts").read_text(
        encoding="utf-8"
    )
    assert "formatReadCatchMessage" in peel or "sak493-g" in peel
    assert "formatReadCatchMessage" in hook or "peelMissFromFetchError" in hook


def test_sak493_h_sdk_readiness_markers() -> None:
    """sak493-h: SDK health/modules/capacity empty-vs-miss tagged."""
    root = Path(__file__).resolve().parents[3] / "SwissArmyNoife"
    py = (root / "sdks" / "python" / "src" / "swissarmynoife" / "client.py").read_text(
        encoding="utf-8"
    )
    ts = (root / "sdks" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")
    rust = (root / "crates" / "sdk" / "src" / "client.rs").read_text(encoding="utf-8")
    assert "sak493-h" in py
    assert "sak493-h" in ts
    assert "sak493-h" in rust
