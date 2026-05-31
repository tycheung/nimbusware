"""``timeline_integrator`` timeline sections."""

from nimbusware_console.pages.run_detail.timeline_integrator.gate_latest import _render_integrator_gate_latest
from nimbusware_console.pages.run_detail.timeline_integrator.gate_history import _render_integrator_gate_history
from nimbusware_console.pages.run_detail.timeline_integrator.gate_delta import _render_integrator_gate_delta

def render_run_detail_timeline_integrator(run_id: str, data: dict) -> None:
    _render_integrator_gate_latest(run_id, data)
    _render_integrator_gate_history(run_id, data)
    _render_integrator_gate_delta(run_id, data)
