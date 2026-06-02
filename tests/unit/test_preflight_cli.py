from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from hermes_orchestrator import preflight_cli, preflight_histogram
from hermes_orchestrator.preflight import PreflightError

# build_histogram


def test_build_histogram_empty_returns_zeroed_stats_and_buckets() -> None:
    hist = preflight_histogram.build_histogram([])
    assert hist["count"] == 0
    assert hist["samples_ms"] == []
    assert hist["min_ms"] is None
    assert hist["max_ms"] is None
    assert hist["mean_ms"] is None
    assert hist["median_ms"] is None
    assert hist["p95_ms"] is None
    # 8 named buckets + overflow ⇒ 9 entries; all counts must be zero
    assert len(hist["buckets"]) == len(preflight_histogram.BUCKET_EDGES_MS) + 1
    assert all(b["count"] == 0 for b in hist["buckets"])
    assert hist["buckets"][-1]["le_ms"] is None
    assert hist["bucket_edges_ms"] == list(preflight_histogram.BUCKET_EDGES_MS)


def test_build_histogram_single_sample_pins_all_stats() -> None:
    hist = preflight_histogram.build_histogram([42])
    assert hist["count"] == 1
    assert hist["samples_ms"] == [42]
    assert hist["min_ms"] == hist["max_ms"] == hist["mean_ms"] == 42
    assert hist["median_ms"] == 42
    assert hist["p95_ms"] == 42
    # 42 falls into the (−1, 50] first bucket
    assert hist["buckets"][0]["le_ms"] == 50
    assert hist["buckets"][0]["count"] == 1
    # Every other bucket including overflow stays zero ⇒ sums to count
    assert sum(b["count"] for b in hist["buckets"]) == 1


def test_build_histogram_partition_contract_buckets_sum_to_count() -> None:
    """Every sample lands in exactly one bucket (non-cumulative partition)."""
    samples = [10, 50, 51, 100, 101, 250, 500, 750, 2400, 4999, 9999, 10_000]
    hist = preflight_histogram.build_histogram(samples)
    assert hist["count"] == len(samples)
    assert sum(b["count"] for b in hist["buckets"]) == len(samples)
    # Edge inclusivity: 50 lands in {le_ms: 50}, 51 lands in {le_ms: 100}
    # 250 falls into (100, 250] alongside 101.
    by_edge = {b["le_ms"]: b["count"] for b in hist["buckets"]}
    assert by_edge[50] == 2  # 10, 50
    assert by_edge[100] == 2  # 51, 100
    assert by_edge[250] == 2  # 101, 250
    assert by_edge[500] == 1  # 500 itself (edge inclusive)
    assert by_edge[10_000] == 2  # 9999, 10000 (10000 is the edge)


def test_build_histogram_overflow_bucket_captures_above_10000ms() -> None:
    hist = preflight_histogram.build_histogram([15_000, 25_000, 10_001])
    assert hist["buckets"][-1]["le_ms"] is None
    assert hist["buckets"][-1]["count"] == 3
    # All named buckets are empty
    assert all(b["count"] == 0 for b in hist["buckets"][:-1])
    assert hist["max_ms"] == 25_000
    assert hist["min_ms"] == 10_001


def test_build_histogram_stats_match_manual_calculation() -> None:
    samples = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    hist = preflight_histogram.build_histogram(samples)
    assert hist["mean_ms"] == sum(samples) // len(samples)  # 55
    # 10 even-length samples ⇒ median is (50 + 60) // 2 == 55
    assert hist["median_ms"] == 55
    # nearest-rank p95 over n=10: ceil(0.95*10)=10 ⇒ s[9] == 100
    assert hist["p95_ms"] == 100


# _samples_from_evidence


def test_samples_from_evidence_prefers_multisample_list() -> None:
    evidence = {
        "health_latency_samples_ms": [120, 130, 125],
        "health_latency_ms": 120,  # fallback should be ignored
    }
    assert preflight_cli._samples_from_evidence(evidence) == [120, 130, 125]


def test_samples_from_evidence_falls_back_to_singleton() -> None:
    evidence: dict[str, Any] = {"health_latency_ms": 150}
    assert preflight_cli._samples_from_evidence(evidence) == [150]


def test_samples_from_evidence_returns_empty_on_garbage() -> None:
    assert preflight_cli._samples_from_evidence(None) == []
    assert preflight_cli._samples_from_evidence({}) == []
    assert preflight_cli._samples_from_evidence({"health_latency_ms": "not-int"}) == []
    # Non-int entries in the list are filtered defensively
    assert preflight_cli._samples_from_evidence(
        {"health_latency_samples_ms": [10, "x", 20, None, 30]},
    ) == [10, 20, 30]


# _env_overrides


def test_env_overrides_restores_prior_env_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_PREFLIGHT_LATENCY_SAMPLES", "7")
    monkeypatch.delenv("HERMES_PREFLIGHT_JSON_PROBE", raising=False)
    with preflight_cli._env_overrides(samples=3, json_probe=True):
        assert os.environ["HERMES_PREFLIGHT_LATENCY_SAMPLES"] == "3"
        assert os.environ["HERMES_PREFLIGHT_JSON_PROBE"] == "1"
    # Both restored: SAMPLES back to "7", JSON_PROBE removed (was unset)
    assert os.environ["HERMES_PREFLIGHT_LATENCY_SAMPLES"] == "7"
    assert "HERMES_PREFLIGHT_JSON_PROBE" not in os.environ


def test_env_overrides_noop_when_both_args_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERMES_PREFLIGHT_LATENCY_SAMPLES", raising=False)
    with preflight_cli._env_overrides(samples=None, json_probe=False):
        assert "HERMES_PREFLIGHT_LATENCY_SAMPLES" not in os.environ
    assert "HERMES_PREFLIGHT_LATENCY_SAMPLES" not in os.environ


# _extract_routing


def test_extract_routing_full_canonical_config() -> None:
    cfg = {
        "runtime": {
            "base_url": "http://ollama:11434",
            "health_endpoint": "/api/tags",
            "request_timeout_seconds": 45,
        },
        "models": {
            "primary": {"id": "llama3.1:8b"},
            "fallbacks": [
                {"id": "qwen2.5-coder:14b"},
                {"id": "phi3"},
            ],
        },
        "preflight": {"min_context_tokens": 4096},
    }
    routing = preflight_cli._extract_routing(cfg)
    assert routing == {
        "base_url": "http://ollama:11434",
        "health_endpoint": "/api/tags",
        "primary_model_id": "llama3.1:8b",
        "fallback_model_ids": ["qwen2.5-coder:14b", "phi3"],
        "preflight_cfg": {"min_context_tokens": 4096},
        "request_timeout_seconds": 45.0,
    }


def test_extract_routing_defensive_defaults_when_missing_keys() -> None:
    routing = preflight_cli._extract_routing({})
    assert routing["base_url"] == "http://localhost:11434"
    assert routing["health_endpoint"] == "/api/tags"
    assert routing["primary_model_id"] == "llama3.1:8b"
    assert routing["fallback_model_ids"] == []
    assert routing["preflight_cfg"] == {}
    assert routing["request_timeout_seconds"] == 10.0


# main


def _stub_preflight_ok(
    *,
    base_url: str,
    health_path: str,
    primary_model_id: str,
    fallback_model_ids: list[str],
    timeout_seconds: float,
    preflight_cfg: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], bool]:
    """Mimic `run_model_preflight` returning a successful multisample probe."""
    _ = (
        base_url,
        health_path,
        fallback_model_ids,
        timeout_seconds,
        preflight_cfg,
    )
    evidence = {
        "runtime_reachable": True,
        "model_available": True,
        "model_id": primary_model_id,
        "health_latency_ms": 120,
        "health_latency_p95_ms": 135,
        "show_latency_ms": 60,
        "p95_latency_ms": 135,
        "health_latency_samples_ms": [120, 130, 135],
        "context_tokens": 8192,
        "checks_passed": [
            "runtime_reachable",
            "model_available",
            "health_latency_measured",
            "health_latency_multisample",
            "context_budget_ok",
        ],
        "preflight_latency_sample_count": 3,
        "p95_latency_source": "max(health_p95_ms,show_latency_ms,optional_json_probe)",
    }
    return primary_model_id, evidence, True


def _read_capsys_json(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    captured = capsys.readouterr()
    line = captured.out.strip()
    assert line, "expected JSON line on stdout"
    return json.loads(line)


def test_main_happy_path_emits_full_schema_json_to_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(preflight_cli, "run_model_preflight", _stub_preflight_ok)
    rc = preflight_cli.main(["--samples", "3"])
    assert rc == 0
    payload = _read_capsys_json(capsys)
    assert payload["schema_version"] == 1
    assert payload["tool"] == "hermes-preflight"
    assert payload["samples_requested"] == 3
    assert payload["samples_used"] == 3
    assert payload["result"]["status"] == "ok"
    assert payload["result"]["selected_model_id"] == "llama3.1:8b"
    assert payload["result"]["used_primary"] is True
    assert payload["result"]["error"] is None
    assert payload["histogram"]["count"] == 3
    assert payload["histogram"]["samples_ms"] == [120, 130, 135]
    assert payload["histogram"]["p95_ms"] == 135
    # Buckets sum to count (partition contract preserved through main)
    assert sum(b["count"] for b in payload["histogram"]["buckets"]) == 3


def test_main_preflight_error_returns_exit_1_with_failed_status(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_pe(**_: object) -> tuple[str, dict[str, Any], bool]:
        raise PreflightError("runtime not reachable: connection refused")

    monkeypatch.setattr(preflight_cli, "run_model_preflight", raise_pe)
    rc = preflight_cli.main([])
    assert rc == 1
    payload = _read_capsys_json(capsys)
    assert payload["result"]["status"] == "failed"
    assert payload["result"]["selected_model_id"] is None
    assert "connection refused" in payload["result"]["error"]
    # Empty histogram on failure (no samples to chart)
    assert payload["histogram"]["count"] == 0


def test_main_missing_config_returns_exit_2_with_error_record(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "does-not-exist.yaml"
    rc = preflight_cli.main(["--config", str(missing)])
    assert rc == 2
    payload = _read_capsys_json(capsys)
    assert payload["result"]["status"] == "error"
    assert payload["result"]["exit_code"] == 2
    assert "config not found" in payload["result"]["error"]


def test_main_rejects_samples_below_one_with_exit_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = preflight_cli.main(["--samples", "0"])
    assert rc == 2
    payload = _read_capsys_json(capsys)
    assert payload["result"]["status"] == "error"
    assert "samples must be >=1" in payload["result"]["error"]


def test_main_writes_json_to_output_file_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(preflight_cli, "run_model_preflight", _stub_preflight_ok)
    out_path = tmp_path / "preflight.json"
    rc = preflight_cli.main(["--samples", "3", "--output", str(out_path)])
    assert rc == 0
    captured = capsys.readouterr()
    # Nothing on stdout when --output is a real file
    assert captured.out == ""
    assert out_path.exists()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["result"]["status"] == "ok"
    assert payload["histogram"]["samples_ms"] == [120, 130, 135]


def test_main_samples_flag_propagates_into_run_model_preflight_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--samples N` sets HERMES_PREFLIGHT_LATENCY_SAMPLES inside the probe."""
    observed: dict[str, str | None] = {}

    def spy_preflight(**kwargs: object) -> tuple[str, dict[str, Any], bool]:
        observed["env_samples"] = os.environ.get("HERMES_PREFLIGHT_LATENCY_SAMPLES")
        observed["env_json_probe"] = os.environ.get("HERMES_PREFLIGHT_JSON_PROBE")
        return _stub_preflight_ok(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(preflight_cli, "run_model_preflight", spy_preflight)
    monkeypatch.delenv("HERMES_PREFLIGHT_LATENCY_SAMPLES", raising=False)
    monkeypatch.delenv("HERMES_PREFLIGHT_JSON_PROBE", raising=False)
    rc = preflight_cli.main(["--samples", "5", "--json-probe"])
    assert rc == 0
    assert observed["env_samples"] == "5"
    assert observed["env_json_probe"] == "1"
    # Env restored after main returns
    assert "HERMES_PREFLIGHT_LATENCY_SAMPLES" not in os.environ
    assert "HERMES_PREFLIGHT_JSON_PROBE" not in os.environ
    _ = capsys.readouterr()  # consume stdout JSON


def test_main_env_is_reentrant_after_repeated_calls(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two back-to-back main() calls leave env in its original state."""
    monkeypatch.setattr(preflight_cli, "run_model_preflight", _stub_preflight_ok)
    monkeypatch.setenv("HERMES_PREFLIGHT_LATENCY_SAMPLES", "9")
    rc1 = preflight_cli.main(["--samples", "2"])
    rc2 = preflight_cli.main(["--samples", "4"])
    assert rc1 == 0
    assert rc2 == 0
    # Original "9" preserved across both invocations
    assert os.environ["HERMES_PREFLIGHT_LATENCY_SAMPLES"] == "9"
    _ = capsys.readouterr()


def test_main_uses_default_config_path_when_flag_omitted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(preflight_cli, "run_model_preflight", _stub_preflight_ok)
    rc = preflight_cli.main([])
    assert rc == 0
    payload = _read_capsys_json(capsys)
    # Resolves to <repo>/configs/model-routing.yaml
    assert payload["config_path"].endswith("model-routing.yaml")
    assert payload["base_url"] == "http://localhost:11434"
    assert payload["primary_model_id"] == "llama3.1:8b"
