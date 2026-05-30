"""Run detail page sections."""

from nimbusware_console.pages.run_detail.findings_actions import (
    render_run_detail_findings_actions_section,
)
from nimbusware_console.pages.run_detail.summary_timeline import (
    render_run_detail_summary_timeline_section,
)

def render_run_detail_section() -> None:
    render_run_detail_summary_timeline_section()
    render_run_detail_findings_actions_section()
