from __future__ import annotations

import os
from typing import Any

from nimbusware_console.pages.run_detail.timeline_misc_core import (
    _render_timeline_misc_core,
)
from nimbusware_console.pages.run_detail.timeline_misc_preflight import (
    _render_timeline_misc_preflight,
)
from nimbusware_console.pages.run_detail.timeline_misc_scraper import (
    _render_timeline_misc_scraper,
)
from nimbusware_console.pages.run_detail.timeline_misc_security import (
    _render_timeline_misc_security,
)
from nimbusware_console.pages.run_detail.timeline_misc_universal_critique import (
    _render_timeline_misc_universal_critique,
)


def _workflow_profile_pick(data: dict[str, Any]) -> str:
    wf = data.get("workflow_profile") if isinstance(data, dict) else None
    if isinstance(wf, str) and wf.strip():
        return wf.strip()
    from nimbusware_env.env_flags import nimbusware_workflow_profile

    return nimbusware_workflow_profile()


def render_run_detail_timeline_misc(run_id: str, data: dict) -> None:
    _wf_pick = _workflow_profile_pick(data)
    _render_timeline_misc_core(run_id, data, _wf_pick)
    _render_timeline_misc_security(run_id, data, _wf_pick)
    _render_timeline_misc_universal_critique(run_id, data, _wf_pick)
    _render_timeline_misc_scraper(run_id, data, _wf_pick)
    _render_timeline_misc_preflight(run_id, data, _wf_pick)
