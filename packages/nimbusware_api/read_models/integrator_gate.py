"""Backward-compatible shim — logic lives in ``nimbusware_projections``."""

from nimbusware_projections.builders.integrator_gate import (
    integrator_gate_timeline_delta,
    integrator_gate_timeline_entries,
    integrator_gate_timeline_history,
    integrator_gate_timeline_summary,
)

# Legacy private name used by some tests.
_integrator_gate_row_from_event = __import__(
    "nimbusware_projections.builders.integrator_gate",
    fromlist=["integrator_gate_row_from_event"],
).integrator_gate_row_from_event

__all__ = [
    "integrator_gate_timeline_delta",
    "integrator_gate_timeline_entries",
    "integrator_gate_timeline_history",
    "integrator_gate_timeline_summary",
]
