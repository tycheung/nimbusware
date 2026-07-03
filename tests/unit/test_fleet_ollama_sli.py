from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from env.edition import DEFAULT_EDITION, ENTERPRISE_EDITION, ENV_EDITION
from orchestrator.fleet.ollama_sli import (
    merge_preflight_history_aggregate,
    probe_health_latency_ms,
    read_sli_export,
    run_sustained_health_probe,
    write_sli_export,
)


def test_probe_health_latency_ms_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

    def _get(*_a: object, **_k: object) -> _Resp:
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(httpx, "get", _get)
    ok, ms, err = probe_health_latency_ms(
        base_url="http://example",
        health_path="/api/tags",
        timeout_seconds=5.0,
    )
    assert ok is True
    assert ms >= 0
    assert err is None
    assert calls["n"] == 1


def test_sustained_probe_collects_samples(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_FLEET_OLLAMA_SLI_SAMPLES", "3")
    monkeypatch.setenv("NIMBUSWARE_FLEET_OLLAMA_SLI_INTERVAL_SEC", "0")

    class _Resp:
        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _Resp())
    record = run_sustained_health_probe(base_url="http://example")
    assert record["samples_used"] == 3
    assert record["p95_latency_ms"] >= 0
    assert record["histogram"]["count"] == 3


def test_write_and_read_export(tmp_path: Path) -> None:
    path = tmp_path / "sli.json"
    payload = {"p95_latency_ms": 42, "schema_version": 1}
    write_sli_export(payload, path)
    loaded = read_sli_export(path)
    assert loaded == payload


def test_merge_preflight_history_aggregate() -> None:
    history = {
        "max_p95_latency_ms": 100,
        "metrics_export": {"avg_p95_latency_ms": 80.0},
    }
    sustained = {"p95_latency_ms": 250}
    merged = merge_preflight_history_aggregate(history, sustained=sustained)
    assert merged["fleet_sli"]["combined_max_p95_latency_ms"] == 250
    assert merged["sustained_sli"]["p95_latency_ms"] == 250


def test_fleet_ollama_sli_disabled_on_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    from orchestrator.fleet.ollama_sli import fleet_ollama_sli_enabled

    assert not fleet_ollama_sli_enabled()


def test_enterprise_fleet_ollama_sli_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    monkeypatch.setenv("NIMBUSWARE_FLEET_OLLAMA_SLI_EXPORT_PATH", str(tmp_path / "sli.json"))
    write_sli_export(
        {"p95_latency_ms": 99, "schema_version": 1, "kind": "fleet_ollama_sustained_sli"},
        tmp_path / "sli.json",
    )
    from fastapi.testclient import TestClient

    from api.app import app
    from iam.constants import API_KEY_HEADER

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        headers = {API_KEY_HEADER: boot.json()["api_key"]}
        status = client.get("/v1/enterprise/fleet-ollama-sli/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["sustained_export_present"] is True
        agg = client.get(
            "/v1/enterprise/fleet-ollama-sli/preflight-aggregate",
            headers=headers,
            params={"limit": 5},
        )
        assert agg.status_code == 200
        body = agg.json()
        assert "preflight_history" in body
        assert body["fleet_sli"]["sustained_p95_latency_ms"] == 99


def test_cli_stdout_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_FLEET_OLLAMA_SLI_SAMPLES", "1")
    monkeypatch.setenv("NIMBUSWARE_FLEET_OLLAMA_SLI_INTERVAL_SEC", "0")

    class _Resp:
        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(httpx, "get", lambda *_a, **_k: _Resp())
    from orchestrator.fleet_ollama_sli_cli import main

    code = main(["--stdout-only", "--base-url", "http://example"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    parsed = json.loads(out)
    assert parsed["samples_used"] == 1
