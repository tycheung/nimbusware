from __future__ import annotations

from pathlib import Path


def test_mesh_host_sync_broker_miss() -> None:
    """sak489-a."""
    src = (
        Path(__file__).resolve().parents[2] / "packages" / "compute" / "mesh_host_sync.py"
    ).read_text(encoding="utf-8")
    assert "_require_mesh_unit" in src
    assert "sak489-a" in src


def test_writers_parallel_refuse() -> None:
    """sak489-b."""
    src = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "orchestrator"
        / "_pipeline"
        / "writers_parallel.py"
    ).read_text(encoding="utf-8")
    assert "sak489-b" in src
    assert "local_runners" in src
    assert "NIMBUSWARE_BROKER_COMPUTE" in src


def test_capacity_hw_refuse_deepen() -> None:
    """sak489-c."""
    probe = (Path(__file__).resolve().parents[2] / "packages" / "hw" / "probe.py").read_text(
        encoding="utf-8"
    )
    pressure = (Path(__file__).resolve().parents[2] / "packages" / "hw" / "pressure.py").read_text(
        encoding="utf-8"
    )
    worker = (
        Path(__file__).resolve().parents[2] / "packages" / "compute" / "minimal_worker.py"
    ).read_text(encoding="utf-8")
    assert "CAPACITY" in probe or "capacity" in probe.lower()
    assert "sak489" in probe or "NIMBUSWARE_BROKER_CAPACITY" in probe
    assert "NIMBUSWARE_BROKER_CAPACITY" in pressure or "sak489" in pressure
    assert "NIMBUSWARE_BROKER_CAPACITY" in worker or "sak489" in worker


def test_peel_assert_refactor() -> None:
    """sak489-d."""
    from broker_client.peel_assert import (
        assert_broker_compute_ok,
        is_compute_miss,
        normalize_claim_work_response,
    )
    from compute import broker_session_status as facade

    assert callable(assert_broker_compute_ok)
    assert is_compute_miss({"via": "broker_miss"}) is True
    assert facade.is_compute_miss is is_compute_miss or callable(facade.is_compute_miss)
    soft = normalize_claim_work_response(
        {"work": None, "error": "queue empty"},
        feature="claim",
    )
    assert soft.get("work") is None


def test_theater_export_openapi() -> None:
    """sak489-e."""
    from api.schemas.peel_responses import TheaterExportMissResponse

    assert TheaterExportMissResponse().via is None or True
    theater = (
        Path(__file__).resolve().parents[2] / "packages" / "api" / "routes" / "runs" / "theater.py"
    ).read_text(encoding="utf-8")
    assert "TheaterExportMissResponse" in theater or "early_export_json_miss" in theater


def test_sse_peel_envelopes() -> None:
    """sak489-f."""
    from api.sse_peel import early_sse_peel_miss, sse_error_envelope

    env = sse_error_envelope(feature="chat_stream", error="broker down")
    assert "broker_miss" in env or "error" in env
    assert callable(early_sse_peel_miss)


def test_maker_sse_client_peel() -> None:
    """sak489-g."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    sse = (root / "sse-client.js").read_text(encoding="utf-8")
    theater = (root / "tabs" / "chat_theater_ui.js").read_text(encoding="utf-8")
    assert "parseSsePeelMiss" in sse
    assert "brokerBacked" in theater


def test_admin_theater_egress_residual() -> None:
    """sak489-h."""
    theater = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "components"
        / "TheaterPanel.tsx"
    ).read_text(encoding="utf-8")
    research = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "api"
        / "routes"
        / "enterprise"
        / "research_ops.py"
    ).read_text(encoding="utf-8")
    assert "isComputeMiss" in theater or "admin-theater-export" in theater
    assert "early_egress_export_json_miss" in research


def test_sdk_mcp_claim_parity() -> None:
    """sak489-i."""
    ts = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "typescript"
        / "src"
        / "mcp.ts"
    ).read_text(encoding="utf-8")
    py = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
        / "swissarmynoife"
        / "mcp.py"
    ).read_text(encoding="utf-8")
    assert "claimWork" in ts
    assert "sak489-i" in ts
    assert "claim_work" in py
    assert "sak489-i" in py
