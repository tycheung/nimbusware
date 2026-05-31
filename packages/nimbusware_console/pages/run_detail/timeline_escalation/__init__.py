"""``timeline_escalation`` timeline sections."""

from nimbusware_console.pages.run_detail.timeline_escalation.marker_history import _render_self_refinement_marker_history
from nimbusware_console.pages.run_detail.timeline_escalation.run_escalated import _render_run_escalated
from nimbusware_console.pages.run_detail.timeline_escalation.escalated_history import _render_run_escalated_history
from nimbusware_console.pages.run_detail.timeline_escalation.escalated_delta import _render_run_escalated_delta

def render_run_detail_timeline_escalation(run_id: str, data: dict) -> None:
    _render_self_refinement_marker_history(run_id, data)
    _render_run_escalated(run_id, data)
    _render_run_escalated_history(run_id, data)
    _render_run_escalated_delta(run_id, data)
