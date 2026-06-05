from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nimbusware_hw.fleet_hardware import (
    parse_fleet_hosts_env,
    probe_fleet_hardware_hosts,
    run_probe_matrix,
)
from nimbusware_hw.probe import probe_hardware_remote_ssh
from nimbusware_hw.ssh_probe import parse_remote_probe_output, run_ssh_hardware_probe


def test_parse_remote_probe_output_mem_and_cpu() -> None:
    text = """
MemTotal:       32768000 kB
MemAvailable:   16384000 kB
CPU_COUNT=16
"""
    raw = parse_remote_probe_output(text)
    assert raw["tier"] in ("medium", "strong")
    assert raw["ram_total_gb"] == pytest.approx(31.25, rel=0.1)
    assert raw["cpu_count"] == 16


def test_parse_remote_probe_output_gpu_line() -> None:
    text = """
MemTotal:       16000000 kB
MemAvailable:    8000000 kB
CPU_COUNT=4
NVIDIA GeForce RTX 4090, 24564 MiB
"""
    raw = parse_remote_probe_output(text)
    assert len(raw["gpus"]) == 1
    assert raw["gpus"][0]["name"] == "NVIDIA GeForce RTX 4090"


def test_run_ssh_hardware_probe_success() -> None:
    stdout = """
MemTotal:       16000000 kB
MemAvailable:    8000000 kB
CPU_COUNT=4
"""
    with patch("nimbusware_hw.ssh_probe.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
        raw = run_ssh_hardware_probe("gpu-node.internal", identity_path=None)
    assert raw["remote_host"] == "gpu-node.internal"
    assert raw["tier"] in ("weak", "medium", "strong")


def test_probe_hardware_remote_ssh_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_HW_SSH_MOCK", "1")
    raw = probe_hardware_remote_ssh("worker-1.example")
    assert raw["platform"] == "ssh-mock"
    assert raw["remote_host"] == "worker-1.example"


def test_parse_fleet_hosts_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", " a.example , b.example ")
    assert parse_fleet_hosts_env() == ["a.example", "b.example"]


def test_probe_hardware_remote_ssh_no_mock_missing_ssh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.delenv("NIMBUSWARE_HW_SSH_MOCK", raising=False)
    with patch("nimbusware_hw.ssh_probe.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("ssh not found")
        raw = probe_hardware_remote_ssh("unreachable.example")
    assert raw["errors"]
    assert raw["tier"] == "weak"


def test_probe_fleet_hardware_hosts_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", "host-a,host-b")
    monkeypatch.setenv("NIMBUSWARE_HW_SSH_MOCK", "1")

    body = probe_fleet_hardware_hosts()
    assert body["host_count"] == 2
    assert len(body["hosts"]) == 2
    assert body["hosts"][0]["tier"] == "medium"


def test_run_ssh_hardware_probe_ci_skips_without_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_HW_FLEET_HOSTS", raising=False)
    monkeypatch.delenv("NIMBUSWARE_HW_SSH_HOST", raising=False)
    summary = run_probe_matrix()
    assert summary["skipped"] is True
    assert summary["host_count"] == 0


def test_run_ssh_hardware_probe_ci_fleet_mock_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_HW_FLEET_HOSTS", "host-a,host-b")
    monkeypatch.setenv("NIMBUSWARE_HW_SSH_MOCK", "1")
    summary = run_probe_matrix()
    assert summary["skipped"] is False
    assert summary["failed"] == 0
    assert summary["passed"] == 2


def test_run_ssh_hardware_probe_ci_min_tier_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_HW_SSH_HOST", "host-a")
    monkeypatch.setenv("NIMBUSWARE_HW_SSH_MOCK", "1")
    monkeypatch.setenv("NIMBUSWARE_HW_EXPECT_MIN_TIER", "strong")
    summary = run_probe_matrix()
    assert summary["failed"] == 1
    assert "tier_below_expectation" in summary["hosts"][0]["errors"][0]
