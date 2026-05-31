"""Escalation YAML: cumulative findings threshold."""

from __future__ import annotations

from pathlib import Path

import yaml

from hermes_orchestrator.escalation_threshold import (
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_high_severity_findings,
    load_escalate_after_cumulative_stage_failures,
)
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_default_repo_disables_auto_escalate() -> None:
    assert load_auto_escalate_after_cumulative_findings(ROOT) is None
    assert load_escalate_after_cumulative_stage_failures(ROOT) is None
    assert load_escalate_after_cumulative_gate_failures(ROOT) is None
    assert load_escalate_after_cumulative_high_severity_findings(ROOT) is None


def test_threshold_from_policy(tmp_path: Path) -> None:
    cfg = tmp_path / "configs" / "escalation"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "verification": {"auto_escalate_after_cumulative_findings": 2},
            },
        ),
        encoding="utf-8",
    )
    assert load_auto_escalate_after_cumulative_findings(tmp_path) == 2


def test_stage_failure_threshold_from_policy(tmp_path: Path) -> None:
    cfg = tmp_path / "configs" / "escalation"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "verification": {"escalate_after_cumulative_stage_failures": 3},
            },
        ),
        encoding="utf-8",
    )
    assert load_escalate_after_cumulative_stage_failures(tmp_path) == 3


def test_gate_failure_threshold_from_policy(tmp_path: Path) -> None:
    cfg = tmp_path / "configs" / "escalation"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "verification": {"escalate_after_cumulative_gate_failures": 2},
            },
        ),
        encoding="utf-8",
    )
    assert load_escalate_after_cumulative_gate_failures(tmp_path) == 2


def test_high_severity_finding_threshold_from_policy(tmp_path: Path) -> None:
    cfg = tmp_path / "configs" / "escalation"
    cfg.mkdir(parents=True)
    (cfg / "policy.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "verification": {"escalate_after_cumulative_high_severity_findings": 2},
            },
        ),
        encoding="utf-8",
    )
    assert load_escalate_after_cumulative_high_severity_findings(tmp_path) == 2
