"""Projection parity — API read_models vs shared builders."""

from __future__ import annotations

from nimbusware_api.read_models.agent_evaluator import agent_evaluator_timeline_summary
from nimbusware_api.read_models.integrator_gate import (
    integrator_gate_timeline_delta,
    integrator_gate_timeline_entries,
    integrator_gate_timeline_history,
    integrator_gate_timeline_summary,
)
from nimbusware_api.read_models.self_refinement import (
    self_refinement_marker_timeline_entries,
    self_refinement_marker_timeline_history,
    self_refinement_timeline_summary,
)
from nimbusware_api.read_models.universal_critique import (
    universal_critique_timeline_entries,
    universal_critique_timeline_summary,
)
from nimbusware_projections.builders.agent_evaluator import (
    agent_evaluator_timeline_summary as proj_agent_eval_summary,
)
from nimbusware_projections.builders.integrator_gate import (
    integrator_gate_timeline_delta as proj_delta,
    integrator_gate_timeline_entries as proj_entries,
    integrator_gate_timeline_history as proj_history,
    integrator_gate_timeline_summary as proj_summary,
)
from nimbusware_projections.builders.self_refinement import (
    self_refinement_marker_timeline_entries as proj_sr_entries,
    self_refinement_marker_timeline_history as proj_sr_history,
    self_refinement_timeline_summary as proj_sr_summary,
)
from nimbusware_projections.builders.universal_critique import (
    universal_critique_timeline_entries as proj_uc_entries,
    universal_critique_timeline_summary as proj_uc_summary,
)
from nimbusware_api.read_models.security_scan import (
    security_scan_on_verify_timeline_entries,
    security_scan_on_verify_timeline_history,
    security_scan_on_verify_timeline_summary,
)
from nimbusware_projections.builders.security_scan import (
    security_scan_on_verify_timeline_entries as proj_scan_entries,
    security_scan_on_verify_timeline_history as proj_scan_history,
    security_scan_on_verify_timeline_summary as proj_scan_summary,
)
from nimbusware_projections.fields.integrator_gate import (
    INTEGRATOR_GATE_DISPLAY_FIELDS,
    INTEGRATOR_GATE_ROW_KEYS,
)
from nimbusware_projections.fields.security_scan import SECURITY_SCAN_ROW_KEYS


def test_integrator_gate_row_keys_align_with_display_fields() -> None:
    display_keys = {k for k, _ in INTEGRATOR_GATE_DISPLAY_FIELDS}
    core_keys = {
        k
        for k in INTEGRATOR_GATE_ROW_KEYS
        if not k.startswith("bundle_compatibility")
        and k != "selected_bundle_rank"
        and k != "selected_bundle_id"
    }
    assert display_keys <= core_keys | {"selected_bundle_id"}


def test_security_scan_row_keys_non_empty() -> None:
    assert "event_id" in SECURITY_SCAN_ROW_KEYS
    assert "security_scan_exit" in SECURITY_SCAN_ROW_KEYS


def test_integrator_gate_api_shim_delegates_to_projections() -> None:
    sample = [
        {
            "event_type": "gate.decision.emitted",
            "event_id": "e1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"stage_name": "integrator.gate", "verdict": "PASS"},
            "metadata": {"integrator_gate": True, "bundle_id": "b1", "integrator_score": 0.9},
        },
    ]
    assert integrator_gate_timeline_summary(sample) == proj_summary(sample)
    assert integrator_gate_timeline_entries(sample) == proj_entries(sample)
    assert integrator_gate_timeline_history(sample) == proj_history(sample)
    assert integrator_gate_timeline_delta(sample) == proj_delta(sample)


def test_security_scan_api_shim_delegates_to_projections() -> None:
    sample = [
        {
            "event_type": "finding.created",
            "event_id": "f1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"finding_id": "x", "severity": "high"},
            "metadata": {"security_scan_exit": 1, "security_scan_snippet": "bandit"},
        },
    ]
    assert security_scan_on_verify_timeline_summary(sample) == proj_scan_summary(sample)
    assert security_scan_on_verify_timeline_entries(sample) == proj_scan_entries(sample)
    assert security_scan_on_verify_timeline_history(sample) == proj_scan_history(sample)


def test_agent_evaluator_api_shim_delegates_to_projections() -> None:
    sample = [
        {
            "event_type": "stage.started",
            "event_id": "s1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"stage_name": "agent_eval:persona-a", "attempt": 1},
            "metadata": {
                "agent_evaluator": {
                    "evaluation": {"status": "pass", "score": 0.85},
                },
            },
        },
    ]
    assert agent_evaluator_timeline_summary(sample) == proj_agent_eval_summary(sample)


def test_universal_critique_api_shim_delegates_to_projections() -> None:
    sample = [
        {
            "event_type": "gate.decision.emitted",
            "event_id": "g1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"stage_name": "planner.critique", "verdict": "PASS"},
            "metadata": {},
        },
    ]
    assert universal_critique_timeline_summary(sample) == proj_uc_summary(sample)
    assert universal_critique_timeline_entries(sample) == proj_uc_entries(sample)


def test_self_refinement_api_shim_delegates_to_projections() -> None:
    sample = [
        {
            "event_type": "stage.started",
            "event_id": "sr1",
            "occurred_at": "2026-01-01T00:00:00Z",
            "payload": {"stage_name": "self_refinement:policy", "attempt": 1},
            "metadata": {"self_refinement": {"version": "v1"}},
        },
    ]
    assert self_refinement_timeline_summary(sample) == proj_sr_summary(sample)
    assert self_refinement_marker_timeline_entries(sample) == proj_sr_entries(sample)
    assert self_refinement_marker_timeline_history(sample) == proj_sr_history(sample)
