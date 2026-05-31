"""``timeline_personas`` timeline sections."""

from nimbusware_console.pages.run_detail.timeline_personas.persona_assignment import _render_persona_assignment
from nimbusware_console.pages.run_detail.timeline_personas.agent_evaluator import _render_agent_evaluator
from nimbusware_console.pages.run_detail.timeline_personas.self_refinement import _render_self_refinement

def render_run_detail_timeline_personas(run_id: str, data: dict) -> None:
    _render_persona_assignment(run_id, data)
    _render_agent_evaluator(run_id, data)
    _render_self_refinement(run_id, data)
