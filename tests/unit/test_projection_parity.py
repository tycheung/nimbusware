"""Integrator gate projection parity — API read_models vs shared builders."""

from __future__ import annotations

from nimbusware_api.read_models.integrator_gate import (
    integrator_gate_timeline_delta,
    integrator_gate_timeline_entries,
    integrator_gate_timeline_history,
    integrator_gate_timeline_summary,
)
from nimbusware_projections.builders.integrator_gate import (
    integrator_gate_timeline_delta as proj_delta,
    integrator_gate_timeline_entries as proj_entries,
    integrator_gate_timeline_history as proj_history,
    integrator_gate_timeline_summary as proj_summary,
)
from nimbusware_projections.fields.integrator_gate import (
    INTEGRATOR_GATE_DISPLAY_FIELDS,
    INTEGRATOR_GATE_ROW_KEYS,
)


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


def test_api_shim_delegates_to_projections() -> None:
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
