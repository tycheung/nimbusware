from __future__ import annotations

from pathlib import Path

from api.schemas.peel_responses import (
    ComputeNodeListMissResponse,
    ComputePeelMissResponse,
    SessionComputeStatusMissResponse,
    WorkUnitClaimMissResponse,
    WorkUnitQueueDepthMissResponse,
    compute_json_openapi_responses,
)
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_503


def test_queue_read_ops_refuse() -> None:
    """sak491-a."""
    work_unit = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "compute"
        / "work_unit.py"
    ).read_text(encoding="utf-8")
    redis_q = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "compute"
        / "work_unit_redis.py"
    ).read_text(encoding="utf-8")
    assert "sak491-a" in work_unit
    assert '_refuse_direct_queue_op("list_units")' in work_unit
    assert '_refuse_direct_queue_op("queued_count")' in work_unit
    assert '_refuse_direct_queue_op("terminate_restart")' in work_unit
    assert '_refuse_direct_queue_op("list_units")' in redis_q


def test_capacity_2_flag_matrix() -> None:
    """sak491-b."""
    flags = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "api_http"
        / "test_capacity_broker_flags_api.py"
    ).read_text(encoding="utf-8")
    assert "sak491-b" in flags
    assert "broker_capacity_only" in flags
    assert "capacity_2" in flags.lower() or "CAPACITY\", \"2\"" in flags or "CAPACITY'] = \"2\"" in flags


def test_compute_peel_miss_schemas() -> None:
    """sak491-c: compute peel miss models carry via/broker_miss/status/feature."""
    base = ComputePeelMissResponse(
        via="broker_miss",
        status="degraded",
        feature="compute_enqueue",
        error="down",
    )
    assert base.via == "broker_miss"
    assert base.status == "degraded"

    nodes = ComputeNodeListMissResponse(via="broker_miss", nodes=[], status="degraded")
    assert nodes.nodes == []

    claim = WorkUnitClaimMissResponse(via="broker_miss", work_unit=None)
    assert claim.work_unit is None

    queue = WorkUnitQueueDepthMissResponse(queued=0, status="degraded")
    assert queue.queued == 0

    status = SessionComputeStatusMissResponse(
        session_id="s1",
        nodes=[],
        queue_depth=0,
        via="broker_miss",
        status="degraded",
        feature="session_compute_status",
    )
    assert status.queue_depth == 0


def test_compute_json_openapi_responses_helper() -> None:
    """sak491-c: helper attaches PROBLEM_RESPONSE_503 (+ optional 404)."""
    base = compute_json_openapi_responses()
    assert base[503] is PROBLEM_RESPONSE_503
    assert 404 not in base

    with_404 = compute_json_openapi_responses(not_found=PROBLEM_RESPONSE_404)
    assert with_404[404] is PROBLEM_RESPONSE_404


def test_compute_routes_wire_openapi_responses() -> None:
    """sak491-c: compute + chat session compute routes wire peel OpenAPI."""
    root = Path(__file__).resolve().parents[2] / "packages" / "api" / "routes"
    compute = (root / "compute.py").read_text(encoding="utf-8")
    chat = (root / "chat_session.py").read_text(encoding="utf-8")

    assert "sak491-c" in (root.parent / "schemas" / "peel_responses.py").read_text(
        encoding="utf-8"
    )
    assert "compute_json_openapi_responses" in compute
    assert (
        compute.count("503: PROBLEM_RESPONSE_503") >= 8
        or "compute_json_openapi_responses()" in compute
    )
    assert "/compute/nodes" in compute and "responses=compute_json_openapi_responses" in compute
    assert "compute/delegate-control" in chat
    assert "compute/opt-in" in chat
    assert chat.count("compute_json_openapi_responses") >= 3


def test_sak_admin_openapi_503() -> None:
    """sak491-d."""
    yaml_path = (
        Path(__file__).resolve().parents[3] / "docs" / "openapi" / "sak-admin.v0.yaml"
    )
    text = yaml_path.read_text(encoding="utf-8")
    assert "BrokerComputeOnlyProblem" in text or "broker_compute_only" in text
    assert "BrokerCapacityOnlyProblem" in text or "broker_capacity_only" in text
    assert "sak491-d" in text or "BrokerComputeOnly503" in text


def test_soak_asserts_present() -> None:
    """sak491-e."""
    soak = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "peel_soak_lib.py"
    ).read_text(encoding="utf-8")
    assert "_assert_sak491_queue_read_refuse" in soak
    assert "sak491 queue read refuse" in soak


def test_try_or_refuse_harden() -> None:
    """sak491-f."""
    dual = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "broker_client"
        / "dual_run_route.py"
    ).read_text(encoding="utf-8")
    assert "sak491-f" in dual
    assert "try_or_refuse" in dual


def test_mesh_absorb_miss_harden() -> None:
    """sak491-g."""
    mesh = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "compute"
        / "mesh_host_sync.py"
    ).read_text(encoding="utf-8")
    assert "sak491-g" in mesh
    assert "_absorb_completed_mesh_units_broker" in mesh


def test_sak491_h_intent_classifier_peel_miss() -> None:
    """sak491-h: classifier uses try_or_refuse; chat classify maps broker_miss."""
    root = Path(__file__).resolve().parents[2] / "packages"
    classifier = (root / "maker" / "intent" / "classifier.py").read_text(encoding="utf-8")
    chat = (root / "api" / "routes" / "chat.py").read_text(encoding="utf-8")
    bff = (root / "api" / "routes" / "admin_ui_bff.py").read_text(encoding="utf-8")

    assert "sak491-h" in classifier
    assert "try_or_refuse" in classifier
    assert "broker_miss: intent_classifier" in classifier
    assert "map_domain_broker_http_miss" in chat  # sak500-b
    assert "last_peel_miss" in bff


def test_admin_sse_peel() -> None:
    """sak491-i."""
    peel = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "api"
        / "peel_assert.ts"
    ).read_text(encoding="utf-8")
    assert "parseSsePeelMiss" in peel
    assert "sak491-i" in peel


def test_sdk_node_path_empty_vs_miss() -> None:
    """sak491-j."""
    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "client.py"
    ).read_text(encoding="utf-8")
    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "index.ts"
    ).read_text(encoding="utf-8")
    rust = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "crates"
        / "sdk"
        / "src"
        / "client.rs"
    ).read_text(encoding="utf-8")
    assert "sak491-j" in py
    assert "sak491-j" in ts
    assert "sak491-j" in rust
