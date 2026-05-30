#!/usr/bin/env python3
"""Split timeline_misc.py by line ranges (preserves indentation)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "packages/nimbusware_console/pages/run_detail/timeline_misc.py"
lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)

HEADER = "".join(lines[:12])
# Body lines inside render_run_detail_timeline_misc (1-indexed in file)
RANGES: list[tuple[str, str, int, int]] = [
    ("timeline_misc_core", "_render_timeline_misc_core", 14, 39),
    ("timeline_misc_security", "_render_timeline_misc_security", 40, 413),
    ("timeline_misc_universal_critique", "_render_timeline_misc_universal_critique", 414, 589),
    ("timeline_misc_scraper", "_render_timeline_misc_scraper", 590, 732),
    ("timeline_misc_preflight", "_render_timeline_misc_preflight", 733, 883),
]

pkg = ROOT / "packages/nimbusware_console/pages/run_detail"
for filename, fn_name, start, end in RANGES:
    chunk = "".join(lines[start - 1 : end])
    mod = f'''"""Run detail — timeline misc ({filename.replace("timeline_misc_", "")})."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403


def {fn_name}(run_id: str, data: dict, _wf_pick: str) -> None:
    _iroot = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
{chunk}'''
    (pkg / f"{filename}.py").write_text(mod, encoding="utf-8")
    print(f"wrote {filename}.py")

orchestrator = '''"""Run detail — timeline misc panel (orchestrator)."""

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
    return os.environ.get("HERMES_WORKFLOW_PROFILE", "nimbusware_production")


def render_run_detail_timeline_misc(run_id: str, data: dict) -> None:
    _wf_pick = _workflow_profile_pick(data)
    _render_timeline_misc_core(run_id, data, _wf_pick)
    _render_timeline_misc_security(run_id, data, _wf_pick)
    _render_timeline_misc_universal_critique(run_id, data, _wf_pick)
    _render_timeline_misc_scraper(run_id, data, _wf_pick)
    _render_timeline_misc_preflight(run_id, data, _wf_pick)
'''
SRC.write_text(orchestrator, encoding="utf-8")
print("updated timeline_misc.py orchestrator")
