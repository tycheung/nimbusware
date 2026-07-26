from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_503
from api.schemas.peel_responses import (
    CapacityPeelMissResponse,
    FleetMeshStatusMissResponse,
    capacity_json_openapi_responses,
    compute_json_openapi_responses,
)
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.critique.handlers import execute_security_critique_llm
from orchestrator.registry import RoleRegistry
from orchestrator.workflow.scan_critique import SecurityCritiqueBlock
from store.memory import InMemoryEventStore

_ROOT = Path(__file__).resolve().parents[2]


def test_capacity_peel_miss_schema() -> None:
    """sak492-a: capacity peel miss model carries via/broker_miss/status/feature."""
    base = CapacityPeelMissResponse(
        via="broker_miss",
        status="degraded",
        feature="platform_hardware",
        error="down",
        capacity_source="broker",
    )
    assert base.via == "broker_miss"
    assert base.status == "degraded"
    assert base.capacity_source == "broker"


def test_capacity_json_openapi_responses_helper() -> None:
    """sak492-a: helper attaches PROBLEM_RESPONSE_503 (+ optional 404)."""
    base = capacity_json_openapi_responses()
    assert base[503] is PROBLEM_RESPONSE_503
    assert 404 not in base

    with_404 = capacity_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)
    assert with_404[404] is PROBLEM_RESPONSE_404


def test_capacity_routes_wire_openapi_responses() -> None:
    """sak492-a: platform hardware + model routing routes wire peel OpenAPI."""
    root = Path(__file__).resolve().parents[2] / "packages" / "api" / "routes"
    hardware = (root / "platform_hardware.py").read_text(encoding="utf-8")
    routing = (root / "platform_model_routing.py").read_text(encoding="utf-8")
    peel = (
        Path(__file__).resolve().parents[2] / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")

    assert "sak492-a" in peel
    assert "capacity_json_openapi_responses" in hardware
    assert "capacity_json_openapi_responses" in routing
    assert (
        "/platform/hardware" in hardware and "responses=capacity_json_openapi_responses" in hardware
    )
    assert (
        "/platform/models/ranked" in routing
        and "responses=capacity_json_openapi_responses" in routing
    )
    assert "/platform/models/dependencies" in routing
    assert "/platform/models/apply-preset" in routing
    assert "/platform/routing-presets/apply" in routing
    assert hardware.count("capacity_json_openapi_responses") >= 4
    assert routing.count("capacity_json_openapi_responses") >= 4


def test_fleet_mesh_status_miss_schema() -> None:
    """sak492-b: fleet mesh peel miss model carries via/status/nodes/queue_depth."""
    miss = FleetMeshStatusMissResponse(
        via="broker_miss",
        status="degraded",
        feature="fleet_mesh",
        error="down",
        session_id="s1",
        nodes=[],
        queue_depth=0,
    )
    assert miss.via == "broker_miss"
    assert miss.queue_depth == 0


def test_fleet_mesh_route_wires_compute_openapi() -> None:
    """sak492-b: fleet-mesh status + chat session compute routes wire 503 OpenAPI."""
    root = Path(__file__).resolve().parents[2] / "packages" / "api" / "routes"
    fleet = (root / "enterprise" / "fleet_mesh.py").read_text(encoding="utf-8")
    chat = (root / "chat_session.py").read_text(encoding="utf-8")
    peel = (
        Path(__file__).resolve().parents[2] / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")

    assert "sak492-b" in peel
    assert "FleetMeshStatusMissResponse" in peel
    assert "compute_json_openapi_responses" in fleet
    assert "/status" in fleet and "responses=compute_json_openapi_responses" in fleet
    assert chat.count("compute_json_openapi_responses") >= 3
    assert compute_json_openapi_responses()[503] is PROBLEM_RESPONSE_503


# sak492-c: checked-in Admin OpenAPI artifact + CI assertions (app.openapi() may be broken).
SAK492_C_PEEL_OPENAPI: tuple[tuple[str, str], ...] = (
    ("/v1/platform/hardware", "get"),
    ("/v1/platform/models/ranked", "get"),
    ("/v1/platform/models/dependencies", "get"),
    ("/v1/compute/nodes", "get"),
    ("/v1/compute/work-units/queue", "get"),
    ("/v1/enterprise/fleet-mesh/status", "get"),
    ("/v1/chat/sessions/{session_id}/compute/status", "get"),
)


def _openapi_json_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "api"
        / "openapi.json"
    )


def test_sak492_c_openapi_artifact_documents_peel_503() -> None:
    """sak492-c: openapi.json lists 503 problem+json on compute/capacity/fleet-mesh peel paths."""
    spec = json.loads(_openapi_json_path().read_text(encoding="utf-8"))
    for path, method in SAK492_C_PEEL_OPENAPI:
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


def test_sak492_c_peel_routes_source_wire_openapi_helpers() -> None:
    """sak492-c: route sources wire capacity/compute peel OpenAPI helpers (fallback when export breaks)."""
    root = Path(__file__).resolve().parents[2] / "packages" / "api" / "routes"
    compute = (root / "compute.py").read_text(encoding="utf-8")
    hardware = (root / "platform_hardware.py").read_text(encoding="utf-8")
    routing = (root / "platform_model_routing.py").read_text(encoding="utf-8")
    fleet = (root / "enterprise" / "fleet_mesh.py").read_text(encoding="utf-8")
    chat = (root / "chat_session.py").read_text(encoding="utf-8")
    peel = (
        Path(__file__).resolve().parents[2] / "packages" / "api" / "schemas" / "peel_responses.py"
    ).read_text(encoding="utf-8")

    assert "sak492-c" in peel
    assert "/compute/nodes" in compute and "compute_json_openapi_responses" in compute
    assert "/platform/hardware" in hardware and "capacity_json_openapi_responses" in hardware
    assert "/platform/models/ranked" in routing and "capacity_json_openapi_responses" in routing
    assert "/status" in fleet and "responses=compute_json_openapi_responses" in fleet
    assert "/sessions/{session_id}/compute/status" in chat
    assert chat.count("compute_json_openapi_responses") >= 3


def test_broker_session_status_nodes_ok_queue_fail_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-g: nodes-ok + queue-fail → broker_miss/degraded (not via=broker success)."""
    from compute.broker_session_status import broker_session_compute_status

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    nid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    with (
        patch(
            "broker_client.stage_bind.compute.compute_node_via_broker",
            return_value={"nodes": [{"id": nid, "label": "n1", "caps": []}]},
        ),
        patch(
            "broker_client.stage_bind.compute.compute_work_via_broker",
            return_value={"error": "work down", "work": []},
        ),
    ):
        out = broker_session_compute_status("s1", feature="fleet_mesh")
    assert out["via"] == "broker_miss"
    assert out["status"] == "degraded"
    assert out["queue_depth"] == 0
    assert out["nodes"][0]["node_id"] == nid
    assert "work down" in str(out.get("error") or "")


def test_sak492_e_critique_llm_peel_miss_source() -> None:
    """sak492-e: scan critique LLM re-raises broker_miss under peel (not return False)."""
    llm = (_ROOT / "packages" / "orchestrator" / "critique" / "llm.py").read_text(encoding="utf-8")
    tw = (_ROOT / "packages" / "orchestrator" / "test_writer_stage.py").read_text(encoding="utf-8")
    broker = (_ROOT / "packages" / "agent_tools" / "facades" / "llm_broker.py").read_text(
        encoding="utf-8"
    )

    assert "sak492-e" in llm
    assert "broker_miss" in llm
    assert "broker_llm_enabled" in llm
    assert "sak492-e" in tw
    assert "ollama_chat_json_via_plan_patch" in broker
    assert "except Exception" not in broker


def test_sak492_e_critique_llm_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-e: critique LLM peel on — broker_miss propagates (no False/stub path)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_ROOT / "configs" / "roles.yaml")
    run_id = uuid4()
    router = UniversalCritiqueRouter.from_yaml(
        _ROOT / "configs" / "personas" / "critique_pairings.yaml"
    )
    block = SecurityCritiqueBlock(severity_floor="medium")

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: critique_llm: broker down")

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


def test_sak492_e_test_writer_stage_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-e: test-writer stage LLM peel on — broker_miss propagates."""
    from orchestrator.test_writer_stage import run_test_writer_stage

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    monkeypatch.setenv("NIMBUSWARE_USE_LLM", "1")

    def _broker_miss(**_: object) -> dict[str, object]:
        raise RuntimeError("broker_miss: test_writer: broker down")

    with patch(
        "orchestrator.test_writer_stage.ollama_chat_json_via_plan_patch",
        side_effect=_broker_miss,
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            run_test_writer_stage(
                Path("."),
                llm_body_enabled=True,
                llm_stub_fallback=True,
                llm_model_id="m",
            )


def test_broker_client_queue_depth_error_dict_never_broker_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-g: error + queued=0 never via=broker success."""
    from broker_client.client import BrokerClient

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    client = BrokerClient(base_url="http://broker.test")
    with patch.object(
        client,
        "list_work_filtered",
        return_value={"error": "work down", "work": []},
    ):
        with pytest.raises(RuntimeError, match="work down"):
            client.queue_depth("s1")


def test_sak492_d_peel_strict_wiring() -> None:
    """sak492-d: Maker-critical stages wire peel_strict + try_or_refuse."""
    root = Path(__file__).resolve().parents[2] / "packages"
    chat = (root / "orchestrator" / "llm" / "chat_facade.py").read_text(encoding="utf-8")
    refactor = (root / "orchestrator" / "refactor_stage.py").read_text(encoding="utf-8")
    launch = (root / "orchestrator" / "launch" / "launch_evaluator.py").read_text(encoding="utf-8")
    slice_facade = (root / "orchestrator" / "llm" / "slice_facade.py").read_text(encoding="utf-8")

    assert "sak492-d" in chat
    assert "peel_strict" in chat
    assert "try_or_refuse" in chat
    assert "broker_miss: chat_facade" in chat
    assert "peel_strict=True" in refactor
    assert "broker_miss" in refactor
    assert "peel_strict=True" in launch
    assert "broker_miss" in launch
    assert "peel_strict=True" in slice_facade
    assert "_require_broker_chat" in slice_facade


def test_chat_facade_peel_strict_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-d: peel_strict + LLM=1 — broker miss propagates (no resolver fallback)."""
    from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    with patch("orchestrator.llm.chat_facade.try_broker_chat_json", return_value=None):
        with pytest.raises(RuntimeError, match="broker_miss"):
            ollama_chat_json_via_plan_patch(
                base_url="http://ollama",
                model="m",
                messages=[{"role": "user", "content": "x"}],
                peel_strict=True,
            )


def test_chat_facade_peel_strict_off_broker_miss_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak492-d: peel_strict + LLM=0 — keep resolver/ollama fallback on broker miss."""
    from orchestrator.llm.chat_facade import ollama_chat_json_via_plan_patch

    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    resolver = MagicMock()
    resolver.chat_json.return_value = {"via": "resolver"}
    with (
        patch("orchestrator.llm.chat_facade.try_broker_chat_json", return_value=None),
        patch("orchestrator.model_routing.preflight.agent_role_for_stage", return_value="planner"),
        patch("orchestrator.collab.mesh_hydrate.ensure_mesh_binding_for_llm"),
        patch("env.find_repo_root", return_value="/repo"),
        patch("orchestrator.model_routing.resolver.ModelBindingResolver", return_value=resolver),
        patch("orchestrator.collab.mesh_context.mesh_participant_overrides", return_value={}),
        patch("orchestrator.collab.mesh_context.mesh_actor_user_id", return_value="u1"),
    ):
        out = ollama_chat_json_via_plan_patch(
            base_url="http://ollama",
            model="m",
            messages=[{"role": "user", "content": "x"}],
            agent_role="planner",
            peel_strict=True,
        )
    assert out == {"via": "resolver"}


def test_launch_eval_peel_on_broker_miss_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """sak492-d: launch eval LLM panel propagates broker_miss under LLM=1."""
    from orchestrator.launch.launch_evaluator import fetch_llm_rubric_panel

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "README.md").write_text("demo", encoding="utf-8")
    with (
        patch(
            "orchestrator.launch.launch_evaluator.ollama_base_url",
            return_value="http://ollama",
        ),
        patch(
            "orchestrator.llm.chat_facade.try_broker_chat_json",
            return_value=None,
        ),
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            fetch_llm_rubric_panel(ws)


def test_sak492_f_compute_2_matrix_tests() -> None:
    """sak492-f: COMPUTE=2 broker-down matrix covers enqueue/nodes/queue/register/heartbeat."""
    flags = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "api_http"
        / "test_compute_broker_flags_api.py"
    ).read_text(encoding="utf-8")
    assert "sak492-f" in flags
    assert "test_enqueue_under_compute_2_broker_down_returns_503" in flags
    assert "test_nodes_list_under_compute_2_broker_down_returns_503" in flags
    assert "test_queue_depth_under_compute_2_broker_down_returns_503" in flags
    assert "test_register_under_compute_2_broker_down_returns_503" in flags
    assert "test_heartbeat_under_compute_2_broker_down_returns_503" in flags


def test_sak492_h_sdk_work_write_markers() -> None:
    """sak492-h: SDK work-write empty-vs-miss tagged across Py/TS/Rust."""
    root = Path(__file__).resolve().parents[3] / "SwissArmyNoife"
    py = (root / "sdks" / "python" / "src" / "swissarmynoife" / "client.py").read_text(
        encoding="utf-8"
    )
    ts = (root / "sdks" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")
    rust = (root / "crates" / "sdk" / "src" / "client.rs").read_text(encoding="utf-8")
    assert "sak492-h" in py
    assert "sak492-h" in ts
    assert "sak492-h" in rust


def test_sak492_i_admin_503_peel_map() -> None:
    """sak492-i: admin maps broker_compute/capacity_only 503 to peel miss."""
    peel = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "api"
        / "peel_assert.ts"
    ).read_text(encoding="utf-8")
    client = (
        Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "api" / "client.ts"
    ).read_text(encoding="utf-8")
    assert "sak492-i" in peel
    assert "mapHttp503PeelMiss" in peel
    assert "broker_compute_only" in peel
    assert "broker_capacity_only" in peel
    assert "mapHttp503PeelMiss" in client or "apiJson" in client
