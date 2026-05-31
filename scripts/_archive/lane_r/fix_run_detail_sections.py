#!/usr/bin/env python3
"""Fix indentation in run_detail section modules after mechanical split."""

from __future__ import annotations

from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "packages" / "nimbusware_console" / "pages" / "run_detail"

DEDENT = {
    "summary.py": 4,
    "timeline_integrator.py": 4,
    "timeline_personas.py": 4,
    "timeline_escalation.py": 4,
    "timeline_misc.py": 4,
    "critic_matrix.py": 4,
    "findings.py": 12,
    "actions.py": 4,
}


def _dedent_file(path: Path, spaces: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    in_fn = False
    for line in lines:
        if line.startswith("def render_run_detail_"):
            in_fn = True
            out.append(line)
            continue
        if in_fn and line.strip() and line.startswith(" " * spaces):
            out.append(line[spaces:])
        else:
            out.append(line)
    path.write_text("".join(out), encoding="utf-8")


def _fix_timeline_core() -> None:
    path = PKG / "timeline_core.py"
    text = path.read_text(encoding="utf-8")
    # Keep only the else-body (display) and rebuild load wrapper.
    start = text.index("                st.subheader(\"Timeline\")")
    end = text.index("        return data, events")
    body = text[start:end]
    body_lines = []
    for line in body.splitlines():
        if line.startswith("                "):
            body_lines.append("        " + line[16:])
        elif line.strip() == "":
            body_lines.append("")
        else:
            body_lines.append(line)
    body_block = "\n".join(body_lines)
    fixed = f'''"""Run detail — timeline load and event table."""

from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

from nimbusware_console.pages.run_detail._imports import *  # noqa: F403
from nimbusware_console.settings import API_BASE


def render_run_detail_timeline_core(run_id: str) -> tuple[dict[str, Any], list] | None:
    if st.button("Load timeline") and run_id.strip():
        try:
            r = httpx.get(f"{{API_BASE}}/runs/{{run_id.strip()}}/timeline", timeout=30.0)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            st.error(f"API error: {{exc}}")
            return None
        events = timeline_events_from_body(data)
{body_block}
        return data, events
    return None
'''
    path.write_text(fixed, encoding="utf-8")


def main() -> None:
    for name, spaces in DEDENT.items():
        _dedent_file(PKG / name, spaces)
    _fix_timeline_core()
    print("Fixed run_detail section indentation")


if __name__ == "__main__":
    main()
