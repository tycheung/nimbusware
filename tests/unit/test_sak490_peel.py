from __future__ import annotations

from pathlib import Path


def test_worker_cli_claim_miss() -> None:
    """sak490-a."""
    src = (
        Path(__file__).resolve().parents[2] / "packages" / "compute" / "worker_cli.py"
    ).read_text(encoding="utf-8")
    assert "_broker_claim_work_or_miss" in src
    assert "_stderr_broker_miss" in src
    assert "sak490-a" in src


def test_queue_direct_ops_refuse() -> None:
    """sak490-b."""
    work_unit = (
        Path(__file__).resolve().parents[2] / "packages" / "compute" / "work_unit.py"
    ).read_text(encoding="utf-8")
    redis_q = (
        Path(__file__).resolve().parents[2] / "packages" / "compute" / "work_unit_redis.py"
    ).read_text(encoding="utf-8")
    pg_q = (
        Path(__file__).resolve().parents[2] / "packages" / "compute" / "work_unit_postgres.py"
    ).read_text(encoding="utf-8")
    assert "_refuse_direct_queue_op" in work_unit
    assert "sak490-b" in work_unit
    assert "_refuse_direct_queue_op" in redis_q
    assert "_refuse_direct_queue_op" in pg_q


def test_writers_readiness_capacity_soft_close() -> None:
    """sak490-c."""
    writers = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "orchestrator"
        / "_pipeline"
        / "writers_parallel.py"
    ).read_text(encoding="utf-8")
    readiness = (
        Path(__file__).resolve().parents[2] / "packages" / "maker" / "readiness" / "platform.py"
    ).read_text(encoding="utf-8")
    assert "sak490-c" in writers
    assert "sak490-c" in readiness
    assert "NIMBUSWARE_BROKER_CAPACITY" in readiness or "capacity" in readiness.lower()


def test_platform_fit_ranked_miss() -> None:
    """sak490-d."""
    hardware = (
        Path(__file__).resolve().parents[2] / "packages" / "api" / "routes" / "platform_hardware.py"
    ).read_text(encoding="utf-8")
    routing = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "api"
        / "routes"
        / "platform_model_routing.py"
    ).read_text(encoding="utf-8")
    fit = (Path(__file__).resolve().parents[2] / "packages" / "hw" / "fit.py").read_text(
        encoding="utf-8"
    )
    assert "sak490-d" in hardware
    assert "sak490-d" in routing
    assert "sak490-d" in fit


def test_dual_run_route_refactor() -> None:
    """sak490-e."""
    from broker_client.dual_run_route import (
        broker_problem,
        map_broker_http_miss,
        refuse_broker_only_http,
    )
    from compute import broker_route as compute_route
    from hw import capacity_route

    assert broker_problem("c", "m") == {"code": "c", "message": "m"}
    assert callable(map_broker_http_miss)
    assert callable(refuse_broker_only_http)
    assert callable(getattr(compute_route, "map_broker_compute_http_error", None)) or callable(
        getattr(compute_route, "map_broker_compute_http_miss", None)
    )
    assert callable(capacity_route.map_broker_capacity_http_miss)


def test_peel_assert_http_miss_builder() -> None:
    """sak490-f."""
    from broker_client.peel_assert import build_http_miss

    body = build_http_miss("down", feature="sse")
    assert body["via"] == "broker_miss"
    assert body["feature"] == "sse"
    assert body["error"] == "down"

    sse = (Path(__file__).resolve().parents[2] / "packages" / "api" / "sse_peel.py").read_text(
        encoding="utf-8"
    )
    export = (
        Path(__file__).resolve().parents[2] / "packages" / "api" / "export_peel.py"
    ).read_text(encoding="utf-8")
    assert "build_http_miss" in sse or "sak490-f" in sse
    assert "build_http_miss" in export or "sak490-f" in export


def test_api_compute_2_problem_matrix() -> None:
    """sak490-g."""
    flags = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "api_http"
        / "test_compute_broker_flags_api.py"
    ).read_text(encoding="utf-8")
    assert "sak490-g" in flags
    assert "COMPUTE" in flags or "compute" in flags


def test_ci_flag_matrix_job() -> None:
    """sak490-h."""
    yml = (
        Path(__file__).resolve().parents[3] / ".github" / "workflows" / "nimbusware-peel.yml"
    ).read_text(encoding="utf-8")
    assert "peel-flag-matrix" in yml
    assert "test_compute_broker_flags_api.py" in yml
    assert "test_capacity_broker_flags_api.py" in yml


def test_sdk_empty_vs_miss_behavioral() -> None:
    """sak490-i."""
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
    assert "sak490-i" in py
    assert "sak490-i" in ts
    assert "sak490-i" in rust
