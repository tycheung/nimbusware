"""``timeline_misc_security`` timeline sections."""

from nimbusware_console.pages.run_detail.timeline_misc_security.scan_on_verify import _render_security_scan_on_verify
from nimbusware_console.pages.run_detail.timeline_misc_security.scan_history import _render_security_scan_history

def _render_timeline_misc_security(run_id: str, data: dict, _wf_pick: str) -> None:
    _render_security_scan_on_verify(run_id, data, _wf_pick)
    _render_security_scan_history(run_id, data, _wf_pick)
