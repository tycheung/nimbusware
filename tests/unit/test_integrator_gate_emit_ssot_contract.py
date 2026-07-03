from __future__ import annotations

from pathlib import Path

import pytest

from console.integrator_core.thresholds import integrator_gate_emission_breakdown
from orchestrator.integrator.gate import integrator_gate_event_would_emit
from unit.composite_repo_fixtures import write_integrator_thresholds


def _mirror(
    repo: Path,
    workflow_profile: str | None,
    *,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    breakdown = integrator_gate_emission_breakdown(repo, workflow_profile)
    assert breakdown["would_emit_integrator_gate_event"] is integrator_gate_event_would_emit(
        repo,
        workflow_profile,
    )


def test_integrator_gate_emit_ssot_env_force_off(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_integrator_thresholds(tmp_path, "version: 1\nenabled: true\n")
    monkeypatch.setenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", "0")
    _mirror(tmp_path, "default", monkeypatch=monkeypatch)


def test_integrator_gate_emit_ssot_thresholds_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    _mirror(tmp_path, "default", monkeypatch=monkeypatch)


def test_integrator_gate_emit_ssot_env_force_on(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_integrator_thresholds(tmp_path, "version: 1\nenabled: false\n")
    monkeypatch.setenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", "1")
    _mirror(tmp_path, "default", monkeypatch=monkeypatch)


def test_integrator_gate_emit_ssot_yaml_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_integrator_thresholds(tmp_path, "version: 1\nenabled: true\n")
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    _mirror(tmp_path, "default", monkeypatch=monkeypatch)


def test_integrator_gate_emit_ssot_workflow_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_integrator_thresholds(tmp_path, "version: 1\nenabled: false\n")
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "demo.yaml").write_text(
        "version: 1\nintegrator_gate:\n  enabled: true\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    _mirror(tmp_path, "demo", monkeypatch=monkeypatch)


def test_integrator_gate_emit_ssot_all_off_with_thresholds_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_integrator_thresholds(tmp_path, "version: 1\nenabled: false\n")
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    _mirror(tmp_path, "default", monkeypatch=monkeypatch)
